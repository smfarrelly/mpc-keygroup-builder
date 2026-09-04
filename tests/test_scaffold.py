import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import drum_builder, entrypoints, plugin_map, scaffold, workstation


class ScaffoldTests(unittest.TestCase):
    def test_all_guided_starters_are_safe_and_honest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for kind in scaffold.KINDS:
                with self.subTest(kind=kind):
                    output = root / kind
                    self.assertEqual(
                        scaffold.create(
                            kind, "My New Sound", output,
                            "house" if kind == "workstation" else "dusty",
                        ),
                        output.resolve(),
                    )
                    receipt = json.loads((output / "scaffold.json").read_text())
                    self.assertEqual(receipt["workflow"], kind)
                    self.assertEqual(receipt["hardware_status"], "deferred")
                    self.assertNotIn(".staging-", (output / "README.md").read_text())
            drum_builder.load_manifest(root / "drum/manifest.toml")
            plugin_map.load_profile(root / "controller-page/profile.toml")
            workstation.load_recipe(
                root / "workstation/Recipes/workstation/house-scratchpad.toml"
            )
            self.assertEqual(
                json.loads((root / "keygroup/scaffold.json").read_text())["software_status"],
                "inputs-required",
            )
            self.assertEqual(
                json.loads((root / "drum/scaffold.json").read_text())["software_status"],
                "inputs-required",
            )

    def test_refuses_existing_output_and_empty_name(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "starter"
            output.mkdir()
            with self.assertRaises(FileExistsError):
                scaffold.create("drum", "Kit", output)
            with self.assertRaisesRegex(ValueError, "non-empty"):
                scaffold.create("drum", "", Path(directory) / "empty")

    def test_front_door_new_command_creates_starter(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "starter"
            rendered = io.StringIO()
            with contextlib.redirect_stdout(rendered):
                status = entrypoints.invoke(
                    "mpc-tools",
                    [
                        "new", "workstation", "--name", "My Session",
                        "--family", "funk", "--output", str(output),
                    ],
                )
            self.assertEqual(status, 0)
            self.assertTrue(
                (output / "Recipes/workstation/funk-scratchpad.toml").is_file()
            )
            self.assertIn("Next: open", rendered.getvalue())


if __name__ == "__main__":
    unittest.main()
