import contextlib
import hashlib
import io
import json
import tempfile
import unittest
import struct
from tests.test_pcm import wav_bytes
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

    def test_optional_audio_verification_detects_truncation_without_mutating_samples(self):
        self.program_file()
        sample = self.root/'kick.wav'
        raw = wav_bytes()
        sample.write_bytes(raw)
        report = check(programs=[self.program], verify_audio=True)
        detail = report['checks'][0]['detail']
        self.assertEqual(report['status'], 'pass')
        self.assertEqual(report['hardware_status'], 'not-evaluated')
        self.assertEqual(detail['audio_verification'], 'pass')
        self.assertEqual(detail['samples'][0]['audio']['pcm_bytes'], 12)
        sample.write_bytes(raw[:-4])
        self.assertEqual(check(programs=[self.program])['status'], 'pass')
        report = check(programs=[self.program], verify_audio=True)
        self.assertEqual(report['status'], 'fail')
        self.assertIn('truncated WAV', report['checks'][0]['detail']['errors'][0])
        self.assertEqual(sample.read_bytes(), raw[:-4])

    def test_audio_verification_records_vendor_riff_adjustment(self):
        self.program_file()
        raw = wav_bytes()
        malformed = raw[:36]+b'atem'+struct.pack('<I',4)+b'abcd'+raw[36:]
        sample = self.root/'kick.wav'
        sample.write_bytes(malformed)
        report = inspect_program(self.program, None, verify_audio=True)
        self.assertEqual(report['audio_verification'], 'pass')
        self.assertTrue(report['samples'][0]['audio']['riff_length_adjusted'])
        self.assertEqual(sample.read_bytes(), malformed)

    def test_audio_verification_does_not_claim_unsupported_or_missing_sources(self):
        self.program_file('kick.aif')
        (self.root/'kick.aif').write_bytes(b'unsupported')
        detail = inspect_program(self.program, None, verify_audio=True)
        self.assertEqual(detail['status'], 'warn')
        self.assertEqual(detail['audio_verification'], 'incomplete')
        self.assertEqual(detail['samples'][0]['audio']['status'], 'unsupported')
        (self.root/'kick.aif').unlink()
        detail = inspect_program(self.program, None, verify_audio=True)
        self.assertEqual(detail['status'], 'fail')
        self.assertNotIn('audio', detail['samples'][0])
        with self.assertRaisesRegex(ValueError, 'requires at least one --program'):
            check(bundles=[self.root], verify_audio=True)

    def test_verify_audio_cli_is_explicit_and_reports_failure(self):
        self.program_file()
        (self.root/'kick.wav').write_bytes(wav_bytes()[:-4])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = invoke('mpc-tools', ['check', '--program', str(self.program), '--verify-audio', '--json'])
        report = json.loads(out.getvalue())
        self.assertEqual(status, 1)
        self.assertTrue(report['audio_verification_requested'])
        self.assertEqual(report['checks'][0]['detail']['audio_verification'], 'fail')

    def test_counted_pcm_padding_is_reported_as_warning_not_silent_success(self):
        self.program_file()
        raw = bytearray(wav_bytes(width=3, channels=1)+b'\0')
        struct.pack_into('<I', raw, 4, len(raw)-8)
        struct.pack_into('<I', raw, 40, 10)
        (self.root/'kick.wav').write_bytes(raw)
        detail = inspect_program(self.program, None, verify_audio=True)
        self.assertEqual(detail['audio_verification'], 'pass')
        self.assertEqual(detail['status'], 'warn')
        self.assertIn('zero alignment byte', detail['warnings'][0])
        self.assertEqual(detail['errors'], [])

    def test_audio_check_bounds_are_inclusive_and_keep_pcm_success_separate(self):
        sample = self.root/'kick.wav'
        sample.write_bytes(wav_bytes())  # Three complete frames.
        for start, end, expected in [(0,2,'pass'), (2,2,'pass'), (0,3,'fail'), (3,4,'fail')]:
            with self.subTest(start=start,end=end):
                self.program_file()
                self.program.write_text(self.program.read_text().replace('</Layer>',
                    f'<SliceStart>{start}</SliceStart><SliceEnd>{end}</SliceEnd></Layer>'))
                detail = inspect_program(self.program, None, verify_audio=True)
                self.assertEqual(detail['audio_verification'], 'pass')
                self.assertEqual(detail['status'], expected)
                self.assertEqual(detail['regions_checked'], 1)
                if expected == 'fail':
                    self.assertEqual(detail['region_issues'][0]['frames'], 3)
                    self.assertIn('outside PCM', detail['errors'][-1])
        self.program_file()
        detail = inspect_program(self.program, None, verify_audio=True)
        self.assertEqual(detail['regions_checked'], 1)
        self.assertEqual(detail['region_issues'], [])
        unchecked = inspect_program(self.program, None)
        self.assertEqual(unchecked['regions_checked'], 0)

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

    def test_uppercase_vendor_extension_and_sample_name_with_dots(self):
        for reference in ('Kick', 'Kick.808'):
            with self.subTest(reference=reference):
                self.program_file(reference)
                (self.root / (reference + '.WAV')).write_bytes(b'fixture')
                report = inspect_program(self.program, None)
                self.assertEqual(report['status'], 'pass')
                self.assertEqual(report['samples'][0]['resolution'], 'case-insensitive')

    def test_case_insensitive_named_directories(self):
        self.program_file('audio/kick.wav')
        (self.root / 'Audio').mkdir()
        target = self.root / 'Audio/KICK.WAV'
        target.write_bytes(b'fixture')
        self.assertEqual(inspect_program(self.program, None)['samples'][0]['path'], str(target))

    def test_case_collisions_are_not_silently_selected(self):
        self.program_file()
        for name in ('kick.wav', 'KICK.WAV'):
            (self.root / name).write_bytes(b'fixture')
        report = inspect_program(self.program, None)
        self.assertEqual(report['status'], 'fail')
        self.assertEqual(report['samples'][0]['status'], 'ambiguous')
        self.assertEqual(len(report['samples'][0]['candidates']), 2)

    def test_companion_and_sibling_duplicates_are_ambiguous(self):
        self.program_file()
        (self.root / 'kick.wav').write_bytes(b'first')
        data = self.root / 'Kit_[ProgramData]'
        data.mkdir()
        (data / 'kick.wav').write_bytes(b'second')
        self.assertEqual(inspect_program(self.program, None)['samples'][0]['status'], 'ambiguous')

    def test_sample_directory_symlink_is_not_followed_even_inside_root(self):
        self.program_file('alias/kick.wav')
        target = self.root / 'actual'
        target.mkdir()
        (target / 'kick.wav').write_bytes(b'fixture')
        (self.root / 'alias').symlink_to(target, target_is_directory=True)
        self.assertEqual(inspect_program(self.program, None)['samples'][0]['status'], 'external')

    def test_directory_case_collisions_are_ambiguous(self):
        self.program_file('audio/kick.wav')
        for folder in ('audio', 'Audio'):
            (self.root / folder).mkdir()
            (self.root / folder / 'kick.wav').write_bytes(b'fixture')
        self.assertEqual(inspect_program(self.program, None)['samples'][0]['status'], 'ambiguous')

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

    def test_truncated_compressed_program_does_not_abort_report(self):
        self.program.write_bytes(b'\x1f\x8b\x08\x00')
        report = check(programs=[self.program, self.root / 'missing.xpm'])
        self.assertEqual(len(report['checks']), 2)
        self.assertEqual(report['status'], 'fail')

    def test_cli_exit_code_and_read_only_behavior(self):
        self.program_file()
        original = self.program.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(invoke('mpc-tools', ['check', '--program', str(self.program), '--json']), 1)
        self.assertEqual(json.loads(output.getvalue())['status'], 'fail')
        self.assertEqual(self.program.read_bytes(), original)
        self.assertEqual(list(self.root.iterdir()), [self.program])
