import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import plugin_audit


class PluginAuditTests(unittest.TestCase):
    def test_reports_versioned_and_unversioned_preset_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            versioned = root / "Vendor - Plugin A"
            (versioned / "Presets").mkdir(parents=True)
            (versioned / "Presets" / "Init.xpl").write_text("preset")
            (versioned / "version.xml").write_text(
                "<plugincontent><identifier>vendor.a</identifier>"
                "<version>1.2.3.4</version></plugincontent>"
            )
            unversioned = root / "Vendor - Plugin B"
            (unversioned / "Presets").mkdir(parents=True)
            (unversioned / "Presets" / "Bass.xpl").write_text("preset")

            report = plugin_audit.audit(root)
            self.assertEqual(report["plugin_content_count"], 2)
            self.assertEqual(report["total_presets"], 2)
            entries = {item["name"]: item for item in report["entries"]}
            self.assertEqual(entries["Vendor - Plugin A"]["version"], "1.2.3.4")
            self.assertEqual(entries["Vendor - Plugin A"]["evidence"], "versioned-content")
            self.assertEqual(entries["Vendor - Plugin B"]["evidence"], "preset-content")
            self.assertIn("does not prove activation", entries["Vendor - Plugin B"]["warnings"][0])

    def test_shared_content_is_not_counted_as_plugin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shared = root / "Generic"
            shared.mkdir()
            (shared / "overlay.json").write_text("{}")
            report = plugin_audit.audit(root)
            self.assertEqual(report["plugin_content_count"], 0)
            self.assertEqual(report["entries"][0]["role"], "shared")
            self.assertEqual(report["entries"][0]["warnings"], [])

    def test_markdown_states_hardware_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Generic").mkdir()
            text = plugin_audit.render_markdown(plugin_audit.audit(root))
            self.assertIn("activation", text)
            self.assertIn("| Name | Evidence |", text)

    def test_rejects_root_and_nested_symbolic_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            synths = root / "Synths"
            synths.mkdir()
            external = root / "external"
            external.mkdir()
            (external / "preset.xpl").write_text("private")

            root_link = synths / "External Plugin"
            root_link.symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "root.*symbolic links"):
                plugin_audit.audit(synths)

            root_link.unlink()
            plugin = synths / "Local Plugin"
            plugin.mkdir()
            (plugin / "broken.xpl").symlink_to(root / "missing.xpl")
            with self.assertRaisesRegex(ValueError, "content.*symbolic links"):
                plugin_audit.audit(synths)


if __name__ == "__main__":
    unittest.main()
