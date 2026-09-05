"""Cache and verify personal copies of official vendor reference documents."""

from __future__ import annotations

import argparse
import hashlib
import importlib.resources
import json
import os
import tempfile
import tomllib
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class ReferenceDocument:
    id: str
    title: str
    publisher: str
    url: str
    filename: str
    redistribution: str
    sha256: str | None


def default_cache_dir() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "mpc-instrument-factory/vendor-documents"


def load_manifest(path: Path | None = None) -> tuple[ReferenceDocument, ...]:
    if path is None:
        text = (
            importlib.resources.files("mpc_keygroup_builder.data")
            .joinpath("vendor-documents.toml")
            .read_text(encoding="utf-8")
        )
        raw = tomllib.loads(text)
    else:
        with path.open("rb") as stream:
            raw = tomllib.load(stream)
    if raw.get("schema_version") != 1:
        raise ValueError("reference manifest requires schema_version=1")
    entries = raw.get("documents")
    if not isinstance(entries, list) or not entries:
        raise ValueError("reference manifest requires [[documents]]")
    result = []
    ids: set[str] = set()
    filenames: set[str] = set()
    for index, item in enumerate(entries, 1):
        if not isinstance(item, dict):
            raise ValueError(f"documents entry {index} must be a table")
        required = ("id", "title", "publisher", "url", "filename", "redistribution")
        missing = [key for key in required if not isinstance(item.get(key), str) or not item[key]]
        if missing:
            raise ValueError(f"documents entry {index} requires: {', '.join(missing)}")
        if item["id"] in ids:
            raise ValueError(f"duplicate document id: {item['id']}")
        if Path(item["filename"]).name != item["filename"] or item["filename"] in filenames:
            raise ValueError(f"invalid or duplicate document filename: {item['filename']}")
        parsed = urlparse(item["url"])
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"document URL must be HTTPS: {item['url']}")
        digest = item.get("sha256")
        if digest is not None and (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError(f"invalid SHA-256 for {item['id']}")
        ids.add(item["id"])
        filenames.add(item["filename"])
        result.append(
            ReferenceDocument(
                item["id"], item["title"], item["publisher"], item["url"],
                item["filename"], item["redistribution"], digest,
            )
        )
    return tuple(result)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _selected(documents: tuple[ReferenceDocument, ...], ids: list[str]) -> tuple[ReferenceDocument, ...]:
    if not ids:
        return documents
    available = {document.id: document for document in documents}
    unknown = sorted(set(ids) - set(available))
    if unknown:
        raise ValueError(f"unknown document id: {', '.join(unknown)}")
    if len(ids) != len(set(ids)):
        raise ValueError("document ids must be unique")
    return tuple(available[item] for item in ids)


def fetch_documents(
    documents: tuple[ReferenceDocument, ...],
    cache_dir: Path,
    *,
    force: bool = False,
) -> dict[str, Any]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    index_path = cache_dir / "index.json"
    if index_path.is_symlink():
        raise ValueError(f"reference cache index may not be a symbolic link: {index_path}")
    records = []
    for document in documents:
        target = cache_dir / document.filename
        if target.is_symlink():
            raise ValueError(f"cached reference may not be a symbolic link: {target}")
        status = "cached"
        if force or not target.is_file():
            request = urllib.request.Request(
                document.url,
                headers={"User-Agent": "mpc-keygroup-builder reference cache/0.1"},
            )
            descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=cache_dir)
            try:
                with os.fdopen(descriptor, "wb") as stream, urllib.request.urlopen(request, timeout=30) as response:
                    content_type = response.headers.get_content_type()
                    if content_type not in {"application/pdf", "application/octet-stream"}:
                        raise ValueError(f"unexpected content type for {document.id}: {content_type}")
                    while chunk := response.read(1024 * 1024):
                        stream.write(chunk)
                    stream.flush()
                    os.fsync(stream.fileno())
                temporary = Path(temporary_name)
                if temporary.stat().st_size < 100:
                    raise ValueError(f"download is unexpectedly small: {document.id}")
                os.replace(temporary, target)
                status = "downloaded"
            finally:
                Path(temporary_name).unlink(missing_ok=True)
        digest = _sha256(target)
        if document.sha256 and digest != document.sha256:
            raise ValueError(
                f"checksum changed for {document.id}: expected {document.sha256}, received {digest}"
            )
        records.append(
            {
                **asdict(document),
                "path": str(target.resolve()),
                "bytes": target.stat().st_size,
                "actual_sha256": digest,
                "status": status,
            }
        )
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "cache_dir": str(cache_dir.resolve()),
        "documents": records,
    }
    index_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def verify_cache(documents: tuple[ReferenceDocument, ...], cache_dir: Path) -> dict[str, Any]:
    results = []
    for document in documents:
        path = cache_dir / document.filename
        if path.is_symlink():
            raise ValueError(f"cached reference may not be a symbolic link: {path}")
        if not path.is_file():
            results.append({"id": document.id, "status": "missing", "path": str(path)})
            continue
        digest = _sha256(path)
        expected = document.sha256
        results.append(
            {
                "id": document.id,
                "status": "pass" if expected is None or digest == expected else "changed",
                "path": str(path.resolve()),
                "sha256": digest,
                "expected_sha256": expected,
            }
        )
    return {"results": results, "verdict": "pass" if all(x["status"] == "pass" for x in results) else "fail"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Korg permits one personal non-commercial copy but prohibits posting its manuals online. This cache is gitignored.",
    )
    parser.add_argument(
        "--manifest", type=Path,
        help="override the packaged maintained-document manifest",
    )
    parser.add_argument(
        "--cache-dir", type=Path, default=default_cache_dir(),
        help="personal cache directory (default: user cache directory)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list", help="list maintained references without downloading")
    list_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    fetch = subparsers.add_parser("fetch", help="download personal copies and write a checksum index")
    fetch.add_argument("--id", action="append", default=[], help="fetch one document id; repeatable")
    fetch.add_argument("--force", action="store_true", help="redownload an existing cached file")
    verify = subparsers.add_parser("verify", help="verify cached files against maintained checksums")
    verify.add_argument("--id", action="append", default=[], help="verify one document id; repeatable")
    args = parser.parse_args()
    manifest = args.manifest.expanduser().resolve() if args.manifest is not None else None
    documents = load_manifest(manifest)
    if args.command == "list":
        if args.json:
            print(json.dumps([asdict(document) for document in documents], indent=2))
        else:
            for document in documents:
                print(f"{document.id}\t{document.title}\t{document.url}")
        return 0
    selected = _selected(documents, args.id)
    cache_dir = args.cache_dir.expanduser().resolve()
    if args.command == "fetch":
        report = fetch_documents(selected, cache_dir, force=args.force)
        for item in report["documents"]:
            print(f"{item['status'].upper()}\t{item['id']}\t{item['actual_sha256']}\t{item['path']}")
        print("Personal cache only; do not commit or redistribute vendor PDFs.")
        return 0
    report = verify_cache(selected, cache_dir)
    for item in report["results"]:
        print(f"{item['status'].upper()}\t{item['id']}\t{item['path']}")
    return 0 if report["verdict"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
