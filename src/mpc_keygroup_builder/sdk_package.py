"""Check an external plugin folder for an MPC CPU target without loading the binary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import struct

from .plugin_params import qlink_locations
from .sdk_params import read_dump


# ELF class, machine, header size, program header size.
TARGETS = {"arm32": (1, 40, 52, 32), "arm64": (2, 183, 64, 56)}
ILLEGAL_FOLDER_CHARS = '"#@,;:<>*^|?\\/'


def manifest_uid(value: object) -> int:
    """Convert the documented FourCC, hex or numeric form to an unsigned UID."""
    if type(value) is int and 0 <= value <= 0xFFFFFFFF:
        return value
    if isinstance(value, str):
        if re.fullmatch(r"0[xX][0-9a-fA-F]{1,8}", value):
            return int(value, 16)
        if len(value) == 4 and all(32 <= ord(c) < 127 for c in value):
            return int.from_bytes(value.encode("ascii"), "big")
        if re.fullmatch(r"[0-9]{1,10}", value) and int(value) <= 0xFFFFFFFF:
            return int(value)
    raise ValueError("plugin.json uid must be a FourCC, unsigned 32-bit integer or hex code")


def package_file(root: Path, relative: str) -> Path:
    # Require portable regular files throughout the supplied path. A link can
    # resolve on this laptop and break when the same folder is copied to exFAT.
    if not isinstance(relative, str) or not relative or "\\" in relative or PureWindowsPath(relative).drive:
        raise ValueError(f"expected a portable relative package path, got {relative!r}")
    rel = PurePosixPath(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError(f"path escapes the plugin folder: {relative!r}")
    path = root
    for part in rel.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"package contains a symbolic link: {path}")
    if not path.is_file():
        raise ValueError(f"missing package file: {path}")
    return path


def inspect_elf(path: Path, target: str) -> dict:
    elf_class, machine, header_size, entry_size = TARGETS[target]
    with path.open("rb") as stream:
        header = stream.read(header_size)
        if len(header) != header_size or header[:7] != bytes([127, 69, 76, 70, elf_class, 1, 1]):
            raise ValueError(f"{path.name}: expected a little-endian {target} ELF shared library")
        if struct.unpack_from("<HHI", header, 16) != (3, machine, 1):
            raise ValueError(f"{path.name}: wrong ELF machine or object type for {target}")
        if target == "arm32":
            phoff = struct.unpack_from("<I", header, 28)[0]
            flags = struct.unpack_from("<I", header, 36)[0]
            if flags & 0xFF000000 != 0x05000000 or flags & 0x600 != 0x400:
                raise ValueError(f"{path.name}: expected ARM EABI5 hard-float calling convention")
        else:
            phoff = struct.unpack_from("<Q", header, 32)[0]
        ehsize, phentsize, phnum = struct.unpack_from("<HHH", header, header_size - 12)
        size = path.stat().st_size
        if (ehsize != header_size or phentsize != entry_size or phnum == 0 or
                phoff < ehsize or phoff + phentsize * phnum > size):
            raise ValueError(f"{path.name}: invalid ELF program header table")
        stream.seek(phoff)
        has_executable_load = False
        for _ in range(phnum):
            segment = stream.read(entry_size)
            seg_type = struct.unpack_from("<I", segment)[0]
            if seg_type != 1:  # PT_LOAD
                continue
            if target == "arm32":
                offset, _, _, filesz, memsz, seg_flags = struct.unpack_from("<6I", segment, 4)
            else:
                seg_flags = struct.unpack_from("<I", segment, 4)[0]
                offset, _, _, filesz, memsz = struct.unpack_from("<5Q", segment, 8)
            if offset + filesz > size or filesz > memsz:
                raise ValueError(f"{path.name}: loadable segment extends outside the ELF image")
            if filesz and seg_flags & 1:
                has_executable_load = True
        if not has_executable_load:
            raise ValueError(f"{path.name}: ELF has no executable load segment")
        stream.seek(0)
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"target": target, "bytes": size, "sha256": digest}


def inspect(root: Path, target: str = "arm32", dump: Path | None = None) -> dict:
    root = root.expanduser().resolve(strict=True)
    manifest = json.loads(package_file(root, "plugin.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("format") != "vst2":
        raise ValueError(f"{root}: expected a standalone MPC vst2 plugin.json")
    for key in ("name", "manufacturer"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            raise ValueError(f"plugin.json requires a nonempty {key}")
    name = manifest["name"]
    vendor = manifest["manufacturer"]
    uid = manifest_uid(manifest.get("uid"))
    expected = f"{vendor} - VST - {name}".translate(str.maketrans("", "", ILLEGAL_FOLDER_CHARS))
    if root.name != expected:
        raise ValueError(f"plugin folder should be named {expected!r} so the MPC can locate the skins")
    outputs = manifest.get("numOutputs", 2)
    inputs = manifest.get("numInputs", 0)
    if type(outputs) is not int or outputs < 1 or type(inputs) is not int or inputs < 0:
        raise ValueError("plugin.json requires valid audio input and output counts")
    kind = manifest.get("kind", "instrument")
    if not isinstance(kind, str) or kind.lower() not in ("instrument", "effect"):
        raise ValueError(f"unrecognized plugin kind: {kind!r}")
    instrument = manifest.get("isInstrument", kind.lower() == "instrument")
    if type(instrument) is not bool:
        raise ValueError("plugin.json isInstrument must be a boolean")
    binary_key = "file"
    if "file32" in manifest or "file64" in manifest:
        binary_key = "file32" if target == "arm32" else "file64"
    if not manifest.get(binary_key):
        raise ValueError(f"plugin.json has no {binary_key} binary for {target}")
    binary = package_file(root, manifest[binary_key])
    info = inspect_elf(binary, target)
    parameter_count = None
    if dump:
        host = read_dump(dump)
        parameter_count = len(host["params"])
        fields = {"name": name, "vendor": vendor, "uidInt": uid,
                  "isInstrument": instrument, "numInputs": inputs, "numOutputs": outputs}
        for key, expected_value in fields.items():
            observed = host[key] & 0xFFFFFFFF if key == "uidInt" else host[key]
            if observed != expected_value:
                raise ValueError(f"SDK dump mismatch for {key}: package {expected_value!r}, dump {observed!r}")
    qlinks = {}
    qlink_file = root / "Plugin Skins" / "Q-Links.json"
    if qlink_file.exists() or qlink_file.is_symlink():
        safe_file = package_file(root, "Plugin Skins/Q-Links.json")
        qlinks = qlink_locations(safe_file, parameter_count)
    return {
        "schema_version": 1, "kind": "mpc-sdk-package-preflight",
        "q_links": qlinks,
        "plugin": name, "vendor": vendor, "uid": uid, "plugin_kind": "instrument" if instrument else "effect",
        "binary": {**info, "path": manifest[binary_key]},
        "install_relative_path": f"VST2 Plugins/{expected}",
        "dump_checked": dump is not None, "hardware_status": "untested",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help='built "<manufacturer> - VST - <name>" folder')
    parser.add_argument("--target", choices=TARGETS, default="arm32", help="original Key 37 uses arm32 (default)")
    parser.add_argument("--sdk-dump", type=Path, help="compare host_sim identity, type and audio buses")
    parser.add_argument("--json", action="store_true", help="print evidence including binary SHA-256")
    args = parser.parse_args(argv)
    report = inspect(args.folder, args.target, args.sdk_dump)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['plugin']} · {args.target} ELF and manifest checked")
        print(f"Binary: {report['binary']['path']}")
        print(f"Package location on MPC media: {report['install_relative_path']}")
    return 0
