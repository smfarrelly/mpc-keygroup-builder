import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mpc_keygroup_builder import web_demo

from mpc_keygroup_builder.web_demo import build_web_demo, demo_bundle


class WebDemoTests(unittest.TestCase):
    def test_bundle_is_synthetic_interactive_and_self_contained(self):
        bundle = demo_bundle()
        self.assertEqual(len(bundle["programs"]), 2)
        self.assertEqual(bundle["devices"][0]["id"], "mpc-key-37")
        self.assertEqual(len(bundle["layouts"]), 3)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "demo.html"
            build_web_demo(output)
            rendered = output.read_text()
            self.assertIn('id="editor-panel"', rendered)
            self.assertIn("Download draft JSON", rendered)
            self.assertNotIn("https://", rendered)
            with self.assertRaises(FileExistsError):
                build_web_demo(output)

    def test_force_refuses_symlink_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "external.html"
            external.write_text("preserve")
            output = root / "demo.html"
            output.symlink_to(external)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                build_web_demo(output, force=True)
            self.assertEqual(external.read_text(), "preserve")

    def test_publication_failure_preserves_previous_demo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "demo.html"
            output.write_text("previous\n")
            with mock.patch.object(web_demo.os, "replace", side_effect=OSError("disk disconnected")):
                with self.assertRaisesRegex(OSError, "disk disconnected"):
                    build_web_demo(output, force=True)
            self.assertEqual(output.read_text(), "previous\n")
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["demo.html"])


if __name__ == "__main__":
    unittest.main()
