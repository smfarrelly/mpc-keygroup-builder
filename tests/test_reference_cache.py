import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder.reference_cache import ReferenceDocument, load_manifest, verify_cache


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


if __name__ == "__main__":
    unittest.main()
