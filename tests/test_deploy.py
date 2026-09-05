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

    def test_manifest_path_must_stay_within_deployment_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local, target = root / "local", root / "sd"
            outside = root / "outside.xpm"
            outside.write_bytes(b"outside")
            manifest = self.manifest(root)
            for unsafe in ("../outside.xpm", str(outside)):
                with self.subTest(sd_path=unsafe):
                    manifest.write_text(
                        manifest.read_text().replace(
                            'sd_path="Programs/Kit.xpm"', f'sd_path="{unsafe}"'
                        )
                    )
                    with self.assertRaisesRegex(ValueError, "relative path|escapes"):
                        deploy.build_plan(manifest, local, target)
                    self.assertEqual(outside.read_bytes(), b"outside")
                    manifest = self.manifest(root)

    def test_target_symlink_cannot_escape_deployment_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local, target, outside = root / "local", root / "sd", root / "outside"
            program = local / "Programs/Kit.xpm"
            program.parent.mkdir(parents=True)
            program.write_bytes(b"new")
            target.mkdir()
            outside.mkdir()
            (target / "Programs").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "escapes"):
                deploy.build_plan(self.manifest(root), local, target)
            self.assertEqual(list(outside.iterdir()), [])

    def test_companion_audio_symlink_cannot_escape_local_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local, target = root / "local", root / "sd"
            program = local / "Programs/Kit.xpm"
            program.parent.mkdir(parents=True)
            program.write_bytes(b"new")
            data = program.with_name("Kit_[ProgramData]")
            data.mkdir()
            outside = root / "outside.wav"
            outside.write_bytes(b"private")
            (data / "Kick.wav").symlink_to(outside)

            with self.assertRaisesRegex(ValueError, "ProgramData.*symbolic links"):
                deploy.build_plan(
                    self.manifest(root), local, target, include_audio=True
                )
            self.assertFalse(target.exists())

    def test_apply_revalidates_target_after_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local, target, outside = root / "local", root / "sd", root / "outside"
            program = local / "Programs/Kit.xpm"
            program.parent.mkdir(parents=True)
            program.write_bytes(b"new")
            plan = deploy.build_plan(self.manifest(root), local, target)

            outside.mkdir()
            target.mkdir()
            (target / "Programs").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "escapes"):
                deploy.apply_plan(plan)
            self.assertFalse((outside / "Kit.xpm").exists())


if __name__ == "__main__":
    unittest.main()
