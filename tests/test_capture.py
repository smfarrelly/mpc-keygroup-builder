import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from mpc_keygroup_builder import capture


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'sd'
        self.source.mkdir()
        self.output = self.root / 'archive'

    def make_pair(self, root: Path, stem: str, content: bytes) -> None:
        (root / f"{stem}.xpj").write_bytes(content)
        data = root / f"{stem}_[ProjectData]"
        data.mkdir()
        (data / "Programs.db").write_bytes(content[::-1])

    def test_copies_and_verifies_two_projects_and_data_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "sd", root / "capture"
            source.mkdir()
            self.make_pair(source, "Key37_Routing_Baseline", b"baseline")
            self.make_pair(source, "Key37_Routing_Changed", b"changed")

            manifest = capture.capture_projects(source, output)

            self.assertEqual((output / "Key37_Routing_Baseline.xpj").read_bytes(), b"baseline")
            self.assertEqual((output / "Key37_Routing_Changed.xpj").read_bytes(), b"changed")
            self.assertEqual(len(manifest["files"]), 4)
            written = json.loads((output / "capture-manifest.json").read_text())
            self.assertEqual(written["changed_setting"], "Key Ranges: Drum Split")
            self.assertTrue(all(len(item["sha256"]) == 64 for item in written["files"]))

    def test_single_idea_captures_note_and_verifies_without_source(self):
        self.make_pair(self.source, 'Late Night', b'idea')
        manifest = capture.capture_projects(self.source, self.output, ('Late Night.xpj',), note='Keep the swung hats')
        self.assertEqual(manifest['note'], 'Keep the swung hats')
        self.assertEqual(manifest['capture_kind'], 'idea-snapshot')
        self.assertEqual(manifest['changed_setting'], '')
        (self.source / 'Late Night.xpj').unlink()
        self.assertEqual(capture.verify_capture(self.output)['files'], 2)

    def test_companion_selection_does_not_confuse_prefix_names(self):
        self.make_pair(self.source, 'Idea', b'first')
        self.make_pair(self.source, 'Idea Extended', b'second')
        capture.capture_projects(self.source, self.output, ('Idea.xpj',))
        self.assertFalse((self.output / 'Idea Extended_[ProjectData]').exists())

    def test_missing_exact_companion_is_not_replaced_with_prefix_match(self):
        (self.source / 'Idea.xpj').write_bytes(b'first')
        self.make_pair(self.source, 'Idea Extended', b'second')
        with self.assertRaisesRegex(ValueError, 'ProjectData'):
            capture.capture_projects(self.source, self.output, ('Idea.xpj',))
        self.assertFalse(self.output.exists())

    def test_rejects_duplicate_and_path_like_names_before_copy(self):
        for names in [(), ('../Idea.xpj',), ('Idea.xpj', 'IDEA.XPJ')]:
            with self.assertRaises(ValueError):
                capture.capture_projects(self.source, self.output, names)
            self.assertFalse(self.output.exists())

    def test_refuses_destination_symlink(self):
        empty = self.root / 'empty'
        empty.mkdir()
        self.output.symlink_to(empty, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symbolic link'):
            capture.capture_projects(self.source, self.output, ('Idea.xpj',))
        self.assertEqual(list(empty.iterdir()), [])

    def _capture_idea(self):
        self.make_pair(self.source, 'Idea', b'idea')
        capture.capture_projects(self.source, self.output, ('Idea.xpj',))

    def test_verifier_detects_modified_missing_and_extra_files(self):
        self._capture_idea()
        target = self.output / 'Idea.xpj'
        target.write_bytes(b'edit')
        with self.assertRaisesRegex(ValueError, 'content changed'):
            capture.verify_capture(self.output)
        target.unlink()
        with self.assertRaisesRegex(ValueError, 'missing capture file'):
            capture.verify_capture(self.output)
        target.write_bytes(b'idea')
        (self.output / 'extra.txt').write_text('extra')
        with self.assertRaisesRegex(ValueError, 'unlisted'):
            capture.verify_capture(self.output)

    def test_verifier_rejects_path_traversal_and_duplicate_manifest_entries(self):
        self._capture_idea()
        path = self.output / 'capture-manifest.json'
        manifest = json.loads(path.read_text())
        original = manifest['files'][0]['destination']
        manifest['files'][0]['destination'] = '../outside.xpj'
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'unsafe capture destination'):
            capture.verify_capture(self.output)
        manifest['files'][0]['destination'] = original
        manifest['files'].append(manifest['files'][0])
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            capture.verify_capture(self.output)

    def test_verifier_refuses_nested_symlink(self):
        self._capture_idea()
        (self.output / 'alias').symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symbolic links'):
            capture.verify_capture(self.output)

    def test_capture_copy_failure_leaves_no_archive_or_staging(self):
        self.make_pair(self.source, 'Idea', b'idea')
        with patch('mpc_keygroup_builder.capture.shutil.copy2', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                capture.capture_projects(self.source, self.output, ('Idea.xpj',))
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob('.archive-*')), [])
        self.assertEqual((self.source / 'Idea.xpj').read_bytes(), b'idea')

    def test_cli_single_project_and_verification(self):
        self.make_pair(self.source, 'Idea', b'idea')
        with patch('sys.argv', ['mpc-project-capture', str(self.source), '--project', 'Idea.xpj', '--note', 'Try sparse drums', '--output', str(self.output)]):
            self.assertEqual(capture.main(), 0)
        with patch('sys.argv', ['mpc-project-capture', '--verify', str(self.output)]):
            self.assertEqual(capture.main(), 0)

    def test_explicit_project_selection_does_not_invent_routing_experiment(self):
        for name in capture.DEFAULT_PROJECTS:
            self.make_pair(self.source, Path(name).stem, b'idea')
        with patch('sys.argv', ['mpc-project-capture', str(self.source), '--output', str(self.output),
                               '--project', capture.DEFAULT_PROJECTS[0], '--project', capture.DEFAULT_PROJECTS[1]]):
            self.assertEqual(capture.main(), 0)
        manifest = json.loads((self.output / 'capture-manifest.json').read_text())
        self.assertEqual(manifest['changed_setting'], '')
        self.assertEqual(manifest['capture_kind'], 'idea-snapshot')

    def test_refuses_missing_project_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sd"
            source.mkdir()
            (source / "Key37_Routing_Baseline.xpj").write_bytes(b"baseline")
            self.make_pair(source, "Key37_Routing_Changed", b"changed")
            with self.assertRaisesRegex(ValueError, "ProjectData"):
                capture.capture_projects(source, root / "capture")

    def test_refuses_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "sd", root / "capture"
            source.mkdir()
            self.make_pair(source, "Key37_Routing_Baseline", b"baseline")
            self.make_pair(source, "Key37_Routing_Changed", b"changed")
            output.mkdir()
            (output / "keep.txt").write_text("preserve")
            with self.assertRaises(FileExistsError):
                capture.capture_projects(source, output)
            self.assertEqual((output / "keep.txt").read_text(), "preserve")

    def test_refuses_nested_symlink_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output, outside = root / "sd", root / "capture", root / "outside"
            source.mkdir()
            outside.mkdir()
            (outside / "private.db").write_bytes(b"outside")
            self.make_pair(source, "Key37_Routing_Baseline", b"baseline")
            self.make_pair(source, "Key37_Routing_Changed", b"changed")
            data = source / "Key37_Routing_Changed_[ProjectData]"
            (data / "external").symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "symbolic links"):
                capture.capture_projects(source, output)

            self.assertFalse(output.exists())
            self.assertEqual((outside / "private.db").read_bytes(), b"outside")


if __name__ == "__main__":
    unittest.main()
