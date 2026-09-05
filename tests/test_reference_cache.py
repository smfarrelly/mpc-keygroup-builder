import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder.reference_cache import (
    ReferenceDocument,
    fetch_documents,
    load_manifest,
    verify_cache,
)


class ReferenceCacheTests(unittest.TestCase):
    def test_repository_manifest_is_strict_and_personal_only(self):
        root = Path(__file__).resolve().parents[1]
        documents = load_manifest(root / "references/vendor-documents.toml")
        packaged = load_manifest()
        self.assertEqual(len(documents), 4)
        self.assertEqual(documents, packaged)
        self.assertTrue(all(item.url.startswith("https://cdn.korg.com/") for item in documents))
        self.assertEqual({item.redistribution for item in documents}, {"personal-copy-only"})

    def test_verify_reports_pass_missing_and_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "doc.pdf"
            path.write_bytes(b"pdf fixture")
            unlocked = ReferenceDocument("one", "One", "Vendor", "https://example.com/a.pdf", "doc.pdf", "personal-copy-only", None)
            self.assertEqual(verify_cache((unlocked,), root)["verdict"], "pass")
            locked = ReferenceDocument("one", "One", "Vendor", "https://example.com/a.pdf", "doc.pdf", "personal-copy-only", "0" * 64)
            self.assertEqual(verify_cache((locked,), root)["results"][0]["status"], "changed")
            path.unlink()
            self.assertEqual(verify_cache((unlocked,), root)["results"][0]["status"], "missing")

    def test_manifest_rejects_non_https_and_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.toml"
            path.write_text(
                'schema_version=1\n[[documents]]\nid="x"\ntitle="X"\npublisher="P"\n'
                'url="http://example.com/x"\nfilename="x.pdf"\nredistribution="personal-copy-only"\n'
            )
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                load_manifest(path)

    def test_cached_document_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "external.pdf"
            external.write_bytes(b"private document")
            cache = root / "cache"
            cache.mkdir()
            (cache / "doc.pdf").symlink_to(external)
            document = ReferenceDocument(
                "one", "One", "Vendor", "https://example.com/doc.pdf",
                "doc.pdf", "personal-copy-only", None,
            )
            with self.assertRaisesRegex(ValueError, "cached reference.*symbolic link"):
                verify_cache((document,), cache)
            with self.assertRaisesRegex(ValueError, "cached reference.*symbolic link"):
                fetch_documents((document,), cache)
            self.assertEqual(external.read_bytes(), b"private document")

    def test_cache_index_symlink_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "cache"
            cache.mkdir()
            (cache / "doc.pdf").write_bytes(b"cached document")
            external = root / "external.json"
            external.write_text("preserve")
            (cache / "index.json").symlink_to(external)
            document = ReferenceDocument(
                "one", "One", "Vendor", "https://example.com/doc.pdf",
                "doc.pdf", "personal-copy-only", None,
            )
            with self.assertRaisesRegex(ValueError, "index.*symbolic link"):
                fetch_documents((document,), cache)
            self.assertEqual(external.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
