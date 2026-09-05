import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import bundle_verify, entrypoints


class BundleVerifyTests(unittest.TestCase):
    @staticmethod
    def bundle(root: Path) -> Path:
        bundle = root / "bundle"
        (bundle / "Programs/Drums").mkdir(parents=True)
        (bundle / "README.md").write_text("portable\n", encoding="utf-8")
        (bundle / "Programs/Drums/idea.mid").write_bytes(b"MThd")
        checksums = {
            path.relative_to(bundle).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(bundle.rglob("*")) if path.is_file()
        }
        (bundle / "checksums.json").write_text(
            json.dumps(checksums, indent=2) + "\n", encoding="utf-8"
        )
        return bundle

    def test_verifies_complete_bundle_and_machine_readable_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = self.bundle(Path(directory))
            report = bundle_verify.verify_bundle(bundle)
            self.assertEqual(report["software_status"], "pass")
            self.assertEqual(report["hardware_status"], "not-evaluated")
            self.assertEqual(report["verified_files"], 2)
            self.assertEqual(len(report["package_sha256"]), 64)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    entrypoints.invoke("mpc-bundle-verify", [str(bundle), "--json"]), 0
                )
            self.assertEqual(json.loads(output.getvalue())["verified_files"], 2)

    def test_rejects_missing_extra_and_changed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = self.bundle(root / "missing")
            (missing / "README.md").unlink()
            with self.assertRaisesRegex(ValueError, "files are missing"):
                bundle_verify.verify_bundle(missing)

            extra = self.bundle(root / "extra")
            (extra / "unrecorded.txt").write_text("extra", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unrecorded files"):
                bundle_verify.verify_bundle(extra)

            changed = self.bundle(root / "changed")
            (changed / "README.md").write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                bundle_verify.verify_bundle(changed)

    def test_rejects_unsafe_receipts_and_every_symbolic_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self.bundle(root / "unsafe")
            receipt_path = bundle / "checksums.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["../outside"] = "0" * 64
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsafe.*path"):
                bundle_verify.verify_bundle(bundle)

            linked = self.bundle(root / "linked")
            (linked / "broken-link").symlink_to(linked / "missing")
            with self.assertRaisesRegex(ValueError, "symbolic links"):
                bundle_verify.verify_bundle(linked)

            receipt_linked = self.bundle(root / "receipt-linked")
            receipt = receipt_linked / "checksums.json"
            external = root / "external-checksums.json"
            receipt.replace(external)
            receipt.symlink_to(external)
            with self.assertRaisesRegex(ValueError, "receipt.*symbolic links"):
                bundle_verify.verify_bundle(receipt_linked)

            parent_linked = self.bundle(root / "parent-linked")
            external_parent = root / "external-parent"
            external_parent.mkdir()
            (parent_linked / "checksums.json").replace(
                external_parent / "checksums.json"
            )
            (parent_linked / "Evidence").symlink_to(
                external_parent, target_is_directory=True
            )
            with self.assertRaisesRegex(ValueError, "receipt.*symbolic links"):
                bundle_verify.verify_bundle(
                    parent_linked, receipt="Evidence/checksums.json"
                )

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO creation is unavailable")
    def test_rejects_unrecorded_special_filesystem_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = self.bundle(Path(directory))
            os.mkfifo(bundle / "unexpected-pipe")
            with self.assertRaisesRegex(ValueError, "unsupported filesystem entry"):
                bundle_verify.verify_bundle(bundle)

    def test_custom_nested_receipt_and_posix_path_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self.bundle(root)
            receipt = bundle / "Evidence/checksums.json"
            receipt.parent.mkdir()
            (bundle / "checksums.json").replace(receipt)
            report = bundle_verify.verify_bundle(
                bundle, receipt="Evidence/checksums.json"
            )
            self.assertEqual(report["verified_files"], 2)
            with self.assertRaisesRegex(ValueError, "unsafe checksum receipt path"):
                bundle_verify.verify_bundle(bundle, receipt=r"Evidence\checksums.json")


if __name__ == "__main__":
    unittest.main()
