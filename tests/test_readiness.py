import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder.capture import capture_projects
from mpc_keygroup_builder.entrypoints import invoke
from mpc_keygroup_builder.readiness import check, inspect_program


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.program = self.root / 'Kit.xpm'

    def program_file(self, reference='kick.wav'):
        self.program.write_text('<MPCVObject><Program type="Drum"><ProgramName>Kit</ProgramName><Instruments><Instrument number="1"><Layers><Layer><SampleFile>' + reference + '</SampleFile></Layer></Layers></Instrument></Instruments></Program></MPCVObject>')

    def test_local_sample_and_missing_reference(self):
        self.program_file()
        self.assertEqual(inspect_program(self.program, None)['status'], 'fail')
        (self.root / 'kick.wav').write_bytes(b'synthetic-placeholder')
        self.assertEqual(inspect_program(self.program, None)['status'], 'pass')

    def test_companion_and_extension_fallback(self):
        self.program_file('kick')
        data = self.root / 'Kit_[ProgramData]'
        data.mkdir()
        (data / 'kick.wav').write_bytes(b'sample')
        self.assertEqual(inspect_program(self.program, None)['samples'][0]['status'], 'found')

    def test_external_reference_is_unknown_not_missing(self):
        for ref in ('/private/kick.wav', 'C:\\audio\\kick.wav', '../../outside.wav'):
            self.program_file(ref)
            report = inspect_program(self.program, None)
            self.assertEqual(report['status'], 'warn')
            self.assertEqual(report['samples'][0]['status'], 'external')

    def test_sample_symlink_cannot_escape_root(self):
        self.program_file()
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'private.wav'
            target.write_bytes(b'private')
            (self.root / 'kick.wav').symlink_to(target)
            self.assertNotEqual(inspect_program(self.program, None)['status'], 'pass')

    def test_explicit_broader_root_supports_parent_reference(self):
        sub = self.root / 'instruments'
        sub.mkdir()
        self.program = sub / 'Kit.xpm'
        self.program_file('../kick.wav')
        (self.root / 'kick.wav').write_bytes(b'sample')
        self.assertEqual(inspect_program(self.program, self.root)['status'], 'pass')

    def test_empty_and_malformed_programs_fail_without_aborting_other_checks(self):
        self.program.write_text('<broken')
        report = check(programs=[self.program, self.root / 'missing.xpm'])
        self.assertEqual(len(report['checks']), 2)
        self.assertTrue(all(row['status'] == 'fail' for row in report['checks']))
        self.program.write_text('<MPCVObject><Program type="Drum"><ProgramName>Empty</ProgramName></Program></MPCVObject>')
        self.assertEqual(inspect_program(self.program, None)['status'], 'fail')

    def test_archive_and_bundle_checks_detect_damage(self):
        source = self.root / 'source'
        source.mkdir()
        (source / 'Idea.xpj').write_bytes(b'project')
        (source / 'Idea_[ProjectData]').mkdir()
        archive = self.root / 'archive'
        capture_projects(source, archive, ('Idea.xpj',))
        bundle = self.root / 'bundle'
        bundle.mkdir()
        (bundle / 'a').write_bytes(b'a')
        (bundle / 'checksums.json').write_text(json.dumps({'a': hashlib.sha256(b'a').hexdigest()}))
        report = check(archives=[archive], bundles=[bundle])
        self.assertEqual(report['status'], 'pass')
        self.assertEqual(report['hardware_status'], 'not-evaluated')
        (bundle / 'a').write_bytes(b'changed')
        self.assertEqual(check(archives=[archive], bundles=[bundle])['status'], 'fail')

    def test_no_implicit_scan_and_unused_root_rejected(self):
        with self.assertRaises(ValueError):
            check()
        with self.assertRaises(ValueError):
            check(archives=[self.root], sample_root=self.root)

    def test_top_level_symlink_refused(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(check(bundles=[alias])['status'], 'fail')

    def test_cli_exit_code_and_read_only_behavior(self):
        self.program_file()
        original = self.program.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(invoke('mpc-tools', ['check', '--program', str(self.program), '--json']), 1)
        self.assertEqual(json.loads(output.getvalue())['status'], 'fail')
        self.assertEqual(self.program.read_bytes(), original)
        self.assertEqual(list(self.root.iterdir()), [self.program])
