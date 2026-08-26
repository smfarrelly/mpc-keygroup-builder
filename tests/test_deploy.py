import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import deploy


class DeployTests(unittest.TestCase):
    def manifest(self, root: Path) -> Path:
        path = root / "candidates.toml"
        path.write_text(
            'schema_version=1\n[[candidates]]\nid="kit"\nledger_path="Kit.xpm"\n'
            'sd_path="Programs/Kit.xpm"\nrole="drums"\nselected=true\n'
        )
        return path

    def test_dry_run_is_additive_and_audio_is_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local, target = root / "local", root / "sd"
            program = local / "Programs/Kit.xpm"
            program.parent.mkdir(parents=True)
            program.write_bytes(b"new")
            data = program.with_name("Kit_[ProgramData]")
            data.mkdir()
            (data / "Kick.wav").write_bytes(b"audio")
            plan = deploy.build_plan(self.manifest(root), local, target)
            self.assertEqual([item["kind"] for item in plan], ["program"])
            self.assertFalse((target / "Programs/Kit.xpm").exists())
            audio_plan = deploy.build_plan(self.manifest(root), local, target, include_audio=True)
            self.assertEqual({item["kind"] for item in audio_plan}, {"program", "audio"})

    def test_replace_requires_and_verifies_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local, target, backup = root / "local", root / "sd", root / "backup"
            for base, value in ((local, b"new"), (target, b"old")):
                path = base / "Programs/Kit.xpm"
                path.parent.mkdir(parents=True)
                path.write_bytes(value)
            plan = deploy.build_plan(self.manifest(root), local, target)
            with self.assertRaisesRegex(ValueError, "backup"):
                deploy.apply_plan(plan)
            deploy.apply_plan(plan, backup)
            self.assertEqual((target / "Programs/Kit.xpm").read_bytes(), b"new")
            self.assertEqual((backup / "Programs/Kit.xpm").read_bytes(), b"old")


if __name__ == "__main__":
    unittest.main()
