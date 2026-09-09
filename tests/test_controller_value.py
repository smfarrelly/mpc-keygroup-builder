import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import controller_value


PROFILE = '''schema_version=1
id="page"
plugin="Test Plugin"
name="Test Page"
description="A test page"
slot=1
channel=9
[[controls]]
control="fader-1"
ui_parameter=1
name="Depth"
priority="core"
'''


def policy(layout: str, *, total: int = 16, core: int = 8) -> str:
    return f'''schema_version=1
name="Test policy"
default_xl3_layout="mix"
max_performance_controls={total}
max_core_controls={core}
[[layouts]]
id="mix"
name="Mix"
kind="mpc-mix"
owner="xl3"
status="primary"
native_panel=false
automation_need="required"
hardware_status="pass"
friction_removed="avoids mixer menus"
{layout}
'''


class ControllerValueTests(unittest.TestCase):
    def test_profiles_are_measured_and_pending_hardware_stays_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "page.toml").write_text(PROFILE)
            source = root / "policy.toml"
            source.write_text(policy('''[[layouts]]
id="page"
name="Page"
kind="mpc-plugin"
owner="xl3"
status="candidate"
native_panel=false
automation_need="optional"
hardware_status="pending"
friction_removed="avoids plugin paging"
profile="page.toml"
'''))

            report = controller_value.analyze(controller_value.load_policy(source))

            page = next(item for item in report["layouts"] if item["id"] == "page")
            self.assertEqual(page["control_count"], 1)
            self.assertEqual(page["core_count"], 1)
            self.assertEqual(page["fader_count"], 1)
            self.assertIn("hardware-pending", {item["code"] for item in report["findings"]})
            self.assertEqual(report["summary"]["errors"], 0)

    def test_flags_budgets_and_primary_external_panel_replication(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "policy.toml"
            source.write_text(policy('''[[layouts]]
id="box"
name="Box"
kind="external-effect"
owner="xl3"
status="primary"
native_panel=true
automation_need="none"
hardware_status="pass"
friction_removed="duplicates a panel"
'''))
            report = controller_value.analyze(controller_value.load_policy(source))
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("panel-replication", codes)
            self.assertIn("native-duplication", codes)

    def test_rejects_profile_path_escape_and_invalid_default(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "policy.toml"
            source.write_text(policy('''[[layouts]]
id="page"
name="Page"
kind="mpc-plugin"
owner="xl3"
status="candidate"
native_panel=false
automation_need="optional"
hardware_status="pending"
friction_removed="avoids paging"
profile="../page.toml"
'''))
            with self.assertRaisesRegex(ValueError, "escapes"):
                controller_value.analyze(controller_value.load_policy(source))
            source.write_text(policy("").replace('default_xl3_layout="mix"', 'default_xl3_layout="missing"'))
            with self.assertRaisesRegex(ValueError, "does not name"):
                controller_value.load_policy(source)

    def test_writes_report_atomically_and_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "policy.toml"
            source.write_text(policy(""))
            report = controller_value.analyze(controller_value.load_policy(source))
            output = root / "output"
            controller_value.write_report(report, output)
            self.assertTrue((output / "controller-value.json").is_file())
            self.assertTrue((output / "HARDWARE_CHECKLIST.md").is_file())
            self.assertIn("**Mix**", (output / "CONTROLLER_VALUE.md").read_text())
            with self.assertRaises(FileExistsError):
                controller_value.write_report(report, output)
            controller_value.write_report(report, output, force=True)
            unsafe = root / "unsafe"
            unsafe.mkdir()
            (unsafe / "keep.txt").write_text("user data")
            with self.assertRaisesRegex(ValueError, "unrecognized"):
                controller_value.write_report(report, unsafe, force=True)
            self.assertEqual((unsafe / "keep.txt").read_text(), "user data")


if __name__ == "__main__":
    unittest.main()
