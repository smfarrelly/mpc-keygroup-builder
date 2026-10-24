import tempfile
import os
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

    def test_stale_source_is_rejected_before_probe_or_staging(self):
        for change in ('modify', 'add', 'remove'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = self.package(root)
                destination = root / 'target'
                plan = package_deploy.build_plan(source, destination)
                if change == 'modify':
                    (source / 'FG Kit.xpm').write_bytes(b'changed')
                elif change == 'add':
                    (source / 'new.txt').write_text('new')
                else:
                    (source / 'audio/Kick.wav').unlink()
                with mock.patch.object(package_deploy, 'write_probe') as probe:
                    with self.assertRaisesRegex(ValueError, 'changed since planning'):
                        package_deploy.apply_package(plan)
                    probe.assert_not_called()
                self.assertFalse(destination.exists())
                self.assertFalse(package_deploy.staging_path(destination).exists())

    def test_empty_destination_is_a_conflict_not_a_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            destination = root / 'target'
            destination.mkdir()
            plan = package_deploy.build_plan(source, destination)
            self.assertEqual(plan['action'], 'conflict')
            with self.assertRaises(FileExistsError):
                package_deploy.apply_package(plan, probe_bytes=0)
            self.assertEqual(list(destination.iterdir()), [])

    def test_last_moment_empty_destination_is_preserved_with_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            destination = root / 'target'
            plan = package_deploy.build_plan(source, destination)
            publish = package_deploy.publish_directory
            def conflict(stage, target):
                target.mkdir()
                return publish(stage, target)
            with mock.patch.object(package_deploy, 'publish_directory', side_effect=conflict):
                with self.assertRaises(FileExistsError):
                    package_deploy.apply_package(plan, probe_bytes=0)
            self.assertEqual(list(destination.iterdir()), [])
            self.assertEqual(package_deploy.inventory(source), package_deploy.inventory(package_deploy.staging_path(destination)))

    def test_source_addition_during_copy_refuses_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            destination = root / 'target'
            plan = package_deploy.build_plan(source, destination)
            copy = package_deploy.copy_file_verified
            def mutate(*args):
                result = copy(*args)
                (source / 'new.txt').write_text('concurrent save')
                return result
            with mock.patch.object(package_deploy, 'copy_file_verified', side_effect=mutate):
                with self.assertRaisesRegex(ValueError, 'changed during copy'):
                    package_deploy.apply_package(plan, probe_bytes=0)
            self.assertFalse(destination.exists())
            self.assertTrue(package_deploy.staging_path(destination).exists())

    def test_malformed_plan_paths_counts_and_stage_do_not_write(self):
        for change in ('path', 'stage', 'count', 'duplicate', 'checksum'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = self.package(root)
                destination = root / 'target'
                plan = package_deploy.build_plan(source, destination)
                if change == 'path':
                    plan['inventory'][0]['relative'] = '../outside'
                elif change == 'stage':
                    plan['staging'] = str(root / 'unrelated')
                elif change == 'count':
                    plan['bytes'] += 1
                elif change == 'duplicate':
                    plan['inventory'].append(plan['inventory'][0])
                else:
                    plan['inventory'][0]['sha256'] = 'invalid'
                with self.assertRaises(ValueError):
                    package_deploy.apply_package(plan, probe_bytes=0)
                self.assertEqual(list(root.iterdir()), [source])

    def test_previously_unchanged_plan_is_rechecked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            target = root / 'target'
            package_deploy.apply_package(package_deploy.build_plan(source, target), probe_bytes=0)
            plan = package_deploy.build_plan(source, target)
            (target / 'FG Kit.xpm').write_bytes(b'changed')
            with self.assertRaises(FileExistsError):
                package_deploy.apply_package(plan, probe_bytes=0)
            self.assertEqual((target / 'FG Kit.xpm').read_bytes(), b'changed')

    def test_case_colliding_directories_are_not_merged(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.package(Path(directory))
            try:
                (source / 'Audio').mkdir()
            except FileExistsError:
                self.skipTest('filesystem is case-insensitive')
            (source / 'Audio/Other.wav').write_bytes(b'other')
            with self.assertRaisesRegex(ValueError, 'case folding'):
                package_deploy.inventory(source)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'requires FIFO support')
    def test_special_files_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.package(Path(directory))
            os.mkfifo(source / 'pipe')
            with self.assertRaisesRegex(ValueError, 'unsupported package'):
                package_deploy.inventory(source)

    def test_windows_does_not_attempt_unsupported_directory_fsync(self):
        with mock.patch.object(package_deploy.os, 'name', 'nt'), mock.patch.object(package_deploy.os, 'open') as open_file:
            package_deploy._fsync_directory(None)
            open_file.assert_not_called()

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

    def test_source_destination_and_staging_must_not_overlap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            cases = (
                (source, source),
                (source, source / "nested-destination"),
                (source, root),
                (root / ".target.mpc-staging", root / "target"),
            )
            for candidate_source, destination in cases:
                with self.subTest(source=candidate_source, destination=destination):
                    if not candidate_source.exists():
                        candidate_source.mkdir()
                        (candidate_source / "program.xpm").write_bytes(b"program")
                    destination_existed = destination.exists()
                    with self.assertRaisesRegex(ValueError, "must not overlap"):
                        package_deploy.build_plan(candidate_source, destination)
                    stage = package_deploy.staging_path(destination)
                    if stage != candidate_source:
                        self.assertFalse(stage.exists())
                    if not destination_existed:
                        self.assertFalse(destination.exists())

    def test_sibling_source_and_destination_are_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            destination = root / "FG Kit Copy"
            plan = package_deploy.build_plan(source, destination)
            self.assertEqual(plan["action"], "create")

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

    def test_report_must_stay_outside_package_trees(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            destination = root / "sd/FG Kit"
            for output, label in (
                (source / "report.json", "source"),
                (destination / "report.json", "destination"),
            ):
                with self.subTest(label=label):
                    with self.assertRaisesRegex(ValueError, f"inside the {label}"):
                        package_deploy.prepare_report(output, source, destination)

    def test_report_rejects_symlinks_and_is_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.package(root)
            destination = root / "sd/FG Kit"
            external = root / "external.json"
            external.write_text("keep\n")
            linked = root / "report.json"
            linked.symlink_to(external)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                package_deploy.prepare_report(linked, source, destination)
            self.assertEqual(external.read_text(), "keep\n")

            output = package_deploy.prepare_report(
                root / "reports/deploy.json", source, destination
            )
            package_deploy.write_report(output, {"status": "planned"})
            self.assertIn('"status": "planned"', output.read_text())


if __name__ == "__main__":
    unittest.main()
