import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mpc_keygroup_builder import capture, idea_archive, entrypoints


class IdeaArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'Idea.xpj').write_bytes(b'project')
        self.data = self.source / 'Idea_[ProjectData]'
        self.data.mkdir()
        (self.data / 'Programs.db').write_bytes(b'programs')
        self.library = self.root / 'library'
        self.archive = self.library / 'take-one'

    def snapshot(self, output=None, **kwargs):
        return capture.capture_projects(self.source, output or self.archive, ('Idea.xpj',), **kwargs)

    def test_preflight_is_no_write_and_counts_exact_payload(self):
        with patch.object(capture, 'sha256', side_effect=AssertionError('unnecessary hashing')):
            report = self.snapshot(dry_run=True)
        self.assertEqual(report['status'], 'planned')
        self.assertEqual(report['bytes'], 15)
        self.assertEqual(len(report['files']), 2)
        self.assertFalse(self.library.exists())

    def test_capture_byte_budget_rejects_without_output(self):
        for limit in (-1, True, 14):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.snapshot(max_bytes=limit)
            self.assertFalse(self.library.exists())
        self.snapshot(max_bytes=15)
        self.assertEqual(capture.verify_capture(self.archive)['bytes'], 15)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'requires POSIX FIFO')
    def test_special_files_rejected_before_copy_and_verify(self):
        pipe = self.data / 'pipe'
        os.mkfifo(pipe)
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            self.snapshot()
        self.assertFalse(self.archive.exists())
        pipe.unlink()
        self.snapshot()
        os.mkfifo(self.archive / 'pipe')
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            capture.verify_capture(self.archive)

    def test_source_mutation_during_copy_aborts_without_publishing(self):
        copy = shutil.copy2
        def mutate(source, destination, **kwargs):
            result = copy(source, destination, **kwargs)
            if Path(source).suffix == '.xpj':
                (self.data / 'Programs.db').write_bytes(b'changed while saving')
            return result
        with patch.object(capture.shutil, 'copy2', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'source changed'):
                self.snapshot()
        self.assertFalse(self.archive.exists())
        self.assertEqual(list(self.library.glob('.take-one-*')), [])

    def test_fingerprint_survives_relocation_and_note_change(self):
        self.snapshot(note='first')
        before = capture.verify_capture(self.archive)['content_sha256']
        other = self.library / 'two'
        self.snapshot(other, note='second')
        self.assertEqual(capture.verify_capture(other)['content_sha256'], before)
        (self.source / 'Idea.xpj').write_bytes(b'changed')
        third = self.library / 'three'
        self.snapshot(third)
        self.assertNotEqual(capture.verify_capture(third)['content_sha256'], before)

    def test_duplicate_json_keys_and_unsafe_paths_are_rejected(self):
        self.snapshot()
        manifest = self.archive / 'capture-manifest.json'
        original = manifest.read_text()
        manifest.write_text(original.replace('"format": 1', '"format": 1, "format": 1'))
        with self.assertRaisesRegex(ValueError, 'duplicate capture manifest key'):
            capture.verify_capture(self.archive)
        for path in ('.', 'C:/outside.xpj', 'Idea_[ProjectData]/file:stream'):
            data = json.loads(original)
            data['files'][0]['destination'] = path
            manifest.write_text(json.dumps(data))
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'unsafe capture destination'):
                capture.verify_capture(self.archive)

    def test_comparison_includes_bytes_and_hashes(self):
        self.snapshot()
        (self.source / 'Idea.xpj').write_bytes(b'longer project')
        other = self.library / 'two'
        self.snapshot(other)
        comparison = capture.compare_captures(self.archive, other)
        self.assertEqual(comparison['byte_delta'], 7)
        self.assertEqual(comparison['changes'][0]['before_bytes'], 7)
        self.assertEqual(comparison['changes'][0]['after_bytes'], 14)
        self.assertNotEqual(comparison['before']['content_sha256'], comparison['after']['content_sha256'])

    def test_index_searches_notes_case_insensitively(self):
        self.snapshot(note='Sparse SWUNG hats')
        self.snapshot(self.library / 'two', note='Dense pads')
        result = idea_archive.list_archives(self.library, query='swung')
        self.assertEqual(result['archives_scanned'], 2)
        self.assertEqual(len(result['matches']), 1)
        self.assertEqual(result['matches'][0]['note'], 'Sparse SWUNG hats')

    def test_index_keeps_invalid_archives_visible_even_with_filter(self):
        self.snapshot(note='good')
        broken = self.library / 'broken'
        self.snapshot(broken)
        (broken / 'Idea.xpj').write_bytes(b'bad')
        result = idea_archive.list_archives(self.library, query='good')
        self.assertEqual(result['invalid_archives'], 1)
        self.assertEqual(len(result['matches']), 1)

    def test_index_skips_directory_symlinks_without_following_them(self):
        self.snapshot()
        (self.library / 'alias').symlink_to(self.source, target_is_directory=True)
        report = idea_archive.list_archives(self.library)
        self.assertEqual(report['archives_scanned'], 1)
        self.assertEqual(len(report['skipped_symlinks']), 1)

    def test_inspect_shows_note_projects_and_fingerprint(self):
        self.snapshot(note='Keep this')
        report = idea_archive.inspect_archive(self.archive)
        self.assertEqual(report['note'], 'Keep this')
        self.assertEqual(report['projects'], ['Idea.xpj'])
        self.assertEqual(len(report['content_sha256']), 64)

    def test_restore_dry_run_does_not_create_parent(self):
        self.snapshot()
        target = self.root / 'missing' / 'experiment'
        report = idea_archive.restore_archive(self.archive, target, dry_run=True)
        self.assertEqual(report['status'], 'planned')
        self.assertFalse(target.parent.exists())

    def test_restore_makes_independent_verified_copy(self):
        self.snapshot()
        target = self.root / 'experiment'
        report = idea_archive.restore_archive(self.archive, target)
        self.assertEqual(report['status'], 'restored')
        self.assertEqual(capture.verify_capture(target)['content_sha256'], report['content_sha256'])
        self.assertNotEqual((target / 'Idea.xpj').stat().st_ino, (self.archive / 'Idea.xpj').stat().st_ino)
        (target / 'Idea.xpj').write_bytes(b'experiment')
        self.assertEqual((self.archive / 'Idea.xpj').read_bytes(), b'project')
        self.assertEqual(capture.verify_capture(self.archive)['status'], 'verified')

    def test_restore_refuses_existing_symlink_and_nested_destinations(self):
        self.snapshot()
        existing = self.root / 'existing'
        existing.mkdir()
        link = self.root / 'link'
        link.symlink_to(self.root / 'missing', target_is_directory=True)
        for target in (existing, link, self.archive):
            with self.assertRaises(FileExistsError):
                idea_archive.restore_archive(self.archive, target)
        with self.assertRaisesRegex(ValueError, 'separate'):
            idea_archive.restore_archive(self.archive, self.archive / 'nested')

    def test_restore_copy_failure_cleans_staging_and_preserves_source(self):
        self.snapshot()
        target = self.root / 'experiment'
        with patch.object(idea_archive.shutil, 'copytree', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                idea_archive.restore_archive(self.archive, target)
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob('.experiment.restore-*')), [])
        self.assertEqual(capture.verify_capture(self.archive)['status'], 'verified')

    def test_restore_source_change_is_rejected(self):
        self.snapshot()
        copy = shutil.copytree
        def mutate(source, target, *args, **kwargs):
            result = copy(source, target, *args, **kwargs)
            if Path(source) == self.archive:
                path = self.archive / 'capture-manifest.json'
                data = json.loads(path.read_text())
                data['note'] = 'concurrent edit'
                path.write_text(json.dumps(data))
            return result
        target = self.root / 'experiment'
        with patch.object(idea_archive.shutil, 'copytree', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed during restore'):
                idea_archive.restore_archive(self.archive, target)
        self.assertFalse(target.exists())

    def test_restore_keyboard_interrupt_cleans_staging_and_preserves_archive(self):
        self.snapshot()
        target = self.root / 'experiment'
        with patch.object(idea_archive.shutil, 'copytree', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                idea_archive.restore_archive(self.archive, target)
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob('.experiment.restore-*')), [])
        self.assertEqual(capture.verify_capture(self.archive)['status'], 'verified')

    def test_restore_destination_appearing_at_publication_survives(self):
        self.snapshot()
        target = self.root / 'experiment'
        publish = idea_archive.publish_directory
        def conflict(stage, destination):
            destination.mkdir()
            return publish(stage, destination)
        with patch.object(idea_archive, 'publish_directory', side_effect=conflict):
            with self.assertRaises(FileExistsError):
                idea_archive.restore_archive(self.archive, target)
        self.assertEqual(list(target.iterdir()), [])
        self.assertEqual(list(self.root.glob('.experiment.restore-*')), [])
        self.assertEqual(capture.verify_capture(self.archive)['status'], 'verified')

    def test_restore_rechecks_destination_after_copy(self):
        self.snapshot()
        target = self.root / 'experiment'
        copy = shutil.copytree
        def conflict(source, staged, *args, **kwargs):
            result = copy(source, staged, *args, **kwargs)
            if Path(source) == self.archive:
                target.mkdir()
                (target / 'keep.txt').write_text('keep')
            return result
        with patch.object(idea_archive.shutil, 'copytree', side_effect=conflict):
            with self.assertRaises(FileExistsError):
                idea_archive.restore_archive(self.archive, target)
        self.assertEqual((target / 'keep.txt').read_text(), 'keep')

    def test_public_cli_end_to_end(self):
        capture_args = [str(self.source), '--project', 'Idea.xpj',
                        '--output', str(self.archive), '--note', 'Groove']
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(entrypoints.invoke('mpc-project-capture', capture_args + ['--dry-run', '--json']), 0)
        self.assertEqual(json.loads(output.getvalue())['bytes'], 15)
        self.assertFalse(self.archive.exists())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(entrypoints.invoke('mpc-project-capture', capture_args), 0)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(entrypoints.invoke('mpc-idea-archive', ['list', str(self.library), '--query', 'groove', '--json']), 0)
        self.assertEqual(len(json.loads(output.getvalue())['matches']), 1)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(entrypoints.invoke('mpc-idea-archive', ['inspect', str(self.archive)]), 0)
            self.assertEqual(entrypoints.invoke('mpc-idea-archive', ['restore', str(self.archive), '--output', str(self.root / 'experiment')]), 0)
        self.assertEqual(capture.verify_capture(self.root / 'experiment')['files'], 2)
        (self.root / 'experiment' / 'Idea.xpj').write_bytes(b'variation')
        variation = self.library / 'take-two'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(entrypoints.invoke('mpc-project-capture', [
                str(self.root / 'experiment'), '--project', 'Idea.xpj',
                '--output', str(variation)]), 0)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(entrypoints.invoke('mpc-project-capture', [
                '--compare', str(self.archive), str(variation), '--json']), 0)
        self.assertEqual(json.loads(output.getvalue())['changed'], ['Idea.xpj'])
        self.assertEqual(capture.verify_capture(self.archive)['status'], 'verified')
