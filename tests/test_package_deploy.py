import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mpc_keygroup_builder import package_deploy


class PackageDeployTests(unittest.TestCase):
    def package(self, root: Path) -> Path:
        source = root / "FG Kit"
        source.mkdir()
        (source / "FG Kit.xpm").write_bytes(b"program")
        (source / "audio").mkdir()
        (source / "audio" / "Kick.wav").write_bytes(b"kick")
        (source / "audio" / "Snare.wav").write_bytes(b"snare")
        return source

    def test_dry_run_inventories_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            destination = root / "sd" / "FG Kit"
            destination.parent.mkdir()
            plan = package_deploy.build_plan(source, destination)
            self.assertEqual(plan["action"], "create")
            self.assertEqual(plan["files"], 3)
            self.assertFalse(destination.exists())
            self.assertEqual(len(plan["package_sha256"]), 64)

    def test_apply_probes_stages_promotes_and_verifies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            destination = root / "sd" / "FG Kit"
            destination.parent.mkdir()
            plan = package_deploy.build_plan(source, destination)
            result = package_deploy.apply_package(plan, probe_bytes=4096)
            self.assertEqual(result["status"], "deployed")
            self.assertEqual(
                package_deploy.inventory(source), package_deploy.inventory(destination)
            )
            self.assertFalse(package_deploy.staging_path(destination).exists())
            self.assertEqual(list(destination.parent.glob(".mpc-write-probe-*")), [])

    def test_identical_destination_is_unchanged_and_conflict_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            destination = root / "sd" / "FG Kit"
            destination.parent.mkdir()
            package_deploy.apply_package(
                package_deploy.build_plan(source, destination), probe_bytes=0
            )
            unchanged = package_deploy.build_plan(source, destination)
            self.assertEqual(unchanged["action"], "unchanged")
            (destination / "FG Kit.xpm").write_bytes(b"different")
            conflict = package_deploy.build_plan(source, destination)
            self.assertEqual(conflict["action"], "conflict")
            with self.assertRaisesRegex(FileExistsError, "different content"):
                package_deploy.apply_package(conflict, probe_bytes=0)

    def test_interrupted_copy_leaves_resumable_stage_not_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            destination = root / "sd" / "FG Kit"
            destination.parent.mkdir()
            plan = package_deploy.build_plan(source, destination)
            original = package_deploy.copy_file_verified
            calls = 0

            def interrupt(source_file, target_file, expected_sha256):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated disconnect")
                original(source_file, target_file, expected_sha256)

            with mock.patch.object(package_deploy, "copy_file_verified", interrupt):
                with self.assertRaisesRegex(OSError, "simulated disconnect"):
                    package_deploy.apply_package(plan, probe_bytes=0)
            self.assertFalse(destination.exists())
            self.assertTrue(package_deploy.staging_path(destination).is_dir())
            with self.assertRaisesRegex(FileExistsError, "--resume"):
                package_deploy.apply_package(plan, probe_bytes=0)
            package_deploy.apply_package(plan, resume=True, probe_bytes=0)
            self.assertEqual(
                package_deploy.inventory(source), package_deploy.inventory(destination)
            )

    def test_resume_refuses_unexpected_staging_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            destination = root / "sd" / "FG Kit"
            destination.parent.mkdir()
            stage = package_deploy.staging_path(destination)
            stage.mkdir()
            (stage / "unrelated.txt").write_text("keep me", encoding="utf-8")
            plan = package_deploy.build_plan(source, destination)
            with self.assertRaisesRegex(ValueError, "unexpected files"):
                package_deploy.apply_package(plan, resume=True, probe_bytes=0)
            self.assertEqual((stage / "unrelated.txt").read_text(), "keep me")

    def test_symbolic_links_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            (source / "link.wav").symlink_to(source / "audio" / "Kick.wav")
            with self.assertRaisesRegex(ValueError, "symbolic links"):
                package_deploy.inventory(source)

    def test_resume_refuses_symlinked_staging_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            destination = root / "sd" / "FG Kit"
            destination.parent.mkdir()
            unrelated = root / "unrelated"
            unrelated.mkdir()
            package_deploy.staging_path(destination).symlink_to(
                unrelated, target_is_directory=True
            )
            plan = package_deploy.build_plan(source, destination)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                package_deploy.apply_package(plan, resume=True, probe_bytes=0)


if __name__ == "__main__":
    unittest.main()
