import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mpc_keygroup_builder import reconcile
from mpc_keygroup_builder.entrypoints import invoke


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.library = self.root / 'library'
        self.library.mkdir()
        self.ledger = self.root / 'ledger.csv'
        self.write_ledger(['Programs/Collection/Kit.xpm'])

    def write_ledger(self, paths):
        with self.ledger.open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['path', 'program_type', 'hardware_status', 'favorite', 'scratchpad_role', 'notes'])
            for path in paths:
                writer.writerow([path, 'Drum', 'pass', 'yes', 'Main drums', 'Keep this sound'])

    def program(self, relative='Collection/Kit.xpm', sample=True):
        path = self.library / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('<MPCVObject><Program type="Drum"><ProgramName>Kit</ProgramName><Instruments><Instrument number="1"><Layers><Layer><SampleFile>kick.wav</SampleFile></Layer></Layers></Instrument></Instruments></Program></MPCVObject>')
        if sample:
            (path.parent / 'kick.wav').write_bytes(b'fixture-only')
        return path

    def collect(self, **kwargs):
        return reconcile.reconcile(self.ledger, [self.library], **kwargs)

    def test_suffix_candidate_is_not_hardware_identity(self):
        path = self.program()
        before = self.ledger.read_bytes()
        result = self.collect()
        row = result['rows'][0]
        self.assertEqual(row['match_status'], 'candidate')
        self.assertEqual(row['hardware_status'], 'pass')
        self.assertEqual(result['hardware_status'], 'not-evaluated')
        self.assertEqual(row['candidates'][0]['path'], str(path))
        self.assertEqual(row['candidates'][0]['sample_status'], 'not-checked')
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_exact_relative_match_and_case_insensitive_suffix(self):
        self.program('Programs/Collection/Kit.xpm')
        self.assertEqual(self.collect()['rows'][0]['candidates'][0]['match_basis'], 'exact-relative')
        self.write_ledger(['PROGRAMS/COLLECTION/KIT.XPM'])
        self.assertEqual(self.collect()['rows'][0]['candidates'][0]['match_basis'], 'path-suffix')

    def test_basename_only_is_never_a_strong_match(self):
        self.program('Other/Kit.xpm')
        report = self.collect()
        self.assertEqual(report['rows'][0]['match_status'], 'name-only')
        self.assertEqual(report['status'], 'attention')

    def test_duplicate_names_remain_ambiguous_even_with_exact_path(self):
        self.program('Programs/Collection/Kit.xpm')
        self.program('Other/Kit.xpm')
        row = self.collect()['rows'][0]
        self.assertEqual(row['match_status'], 'ambiguous')
        self.assertEqual(row['candidate_count'], 2)
        self.assertEqual(row['candidates'][0]['match_basis'], 'exact-relative')

    def test_missing_and_unsafe_paths(self):
        self.write_ledger(['Missing.xpm', '../Kit.xpm', '/Kit.xpm', 'C:\\Kit.xpm'])
        report = self.collect()
        self.assertEqual(report['summary'], {'missing': 1, 'unsafe-ledger-path': 3})

    def test_sample_check_is_opt_in_and_failures_are_visible(self):
        path = self.program(sample=False)
        self.assertEqual(self.collect()['rows'][0]['candidates'][0]['sample_status'], 'not-checked')
        result = self.collect(verify_samples=True)
        candidate = result['rows'][0]['candidates'][0]
        self.assertEqual(candidate['sample_status'], 'fail')
        self.assertEqual(candidate['sample_counts'], {'missing': 1})
        self.assertEqual(result['status'], 'attention')
        (path.parent / 'kick.wav').write_bytes(b'fixture')
        self.assertEqual(self.collect(verify_samples=True)['status'], 'pass')

    def test_malformed_program_does_not_abort_other_rows(self):
        self.program().write_bytes(b'<broken')
        self.program('Collection/Other.xpm')
        self.write_ledger(['Programs/Collection/Kit.xpm', 'Programs/Collection/Other.xpm'])
        result = self.collect(verify_samples=True)
        self.assertEqual([r['candidates'][0]['sample_status'] for r in result['rows']], ['fail', 'pass'])

    def test_symlink_program_and_directory_are_skipped(self):
        external = self.root / 'outside'
        external.mkdir()
        (external / 'Kit.xpm').write_bytes(b'private')
        (self.library / 'Collection').symlink_to(external, target_is_directory=True)
        (self.library / 'Kit.xpm').symlink_to(external / 'Kit.xpm')
        result = self.collect()
        self.assertEqual(result['programs_scanned'], 0)
        self.assertEqual(len(result['skipped_symlinks']), 2)
        self.assertEqual(result['status'], 'attention')

    def test_root_and_ledger_symlinks_are_rejected(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.library, target_is_directory=True)
        with self.assertRaises(ValueError):
            reconcile.inventory([alias])
        ledger_alias = self.root / 'alias.csv'
        ledger_alias.symlink_to(self.ledger)
        with self.assertRaises(ValueError):
            reconcile.reconcile(ledger_alias, [self.library])

    def test_overlapping_and_broad_roots_rejected(self):
        child = self.library / 'child'
        child.mkdir()
        for roots in ([], [self.library, child], [Path('/')], [Path.home()]):
            with self.subTest(roots=roots), self.assertRaises(ValueError):
                reconcile.inventory(roots)

    def test_duplicate_roots_are_deduplicated(self):
        self.program()
        self.assertEqual(len(reconcile.inventory([self.library, self.library])['programs']), 1)

    def test_scan_bounds_fail_instead_of_publishing_partial_success(self):
        self.program()
        for limit in ('MAX_ENTRIES', 'MAX_PROGRAMS'):
            with patch.object(reconcile, limit, 0), self.assertRaises(ValueError):
                self.collect()

    def test_candidates_truncated_explicitly(self):
        for n in range(3):
            self.program(f'Variant{n}/Kit.xpm')
        with patch.object(reconcile, 'MAX_CANDIDATES', 2):
            row = self.collect()['rows'][0]
        self.assertEqual(row['candidate_count'], 3)
        self.assertEqual(len(row['candidates']), 2)
        self.assertTrue(row['candidates_truncated'])

    def test_unmatched_inventory_and_empty_selection(self):
        path = self.program('Collection/Other.xpm')
        report = self.collect(favorite='no')
        self.assertEqual(report['rows'], [])
        self.assertEqual(report['unmatched_programs'][0]['path'], str(path))

    def test_report_outside_inputs_and_no_overwrite(self):
        report = self.collect()
        for output in (self.ledger, self.library / 'report.json'):
            with self.assertRaises((ValueError, FileExistsError)):
                reconcile.write_report(output, report)
        output = self.root / 'reports/new.json'
        reconcile.write_report(output, report)
        self.assertEqual(json.loads(output.read_text())['kind'], 'mpc-library-reconciliation')
        with self.assertRaises(FileExistsError):
            reconcile.write_report(output, report)

    def test_cli_status_json_and_no_modifications(self):
        self.program()
        before = sorted(self.library.rglob('*'))
        with contextlib.redirect_stdout(io.StringIO()) as stream:
            status = invoke('mpc-tools', ['reconcile', '--ledger', str(self.ledger), '--library-root', str(self.library), '--verify-samples', '--json'])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(stream.getvalue())['summary'], {'candidate': 1})
        self.assertEqual(sorted(self.library.rglob('*')), before)

    def test_scan_error_is_attention(self):
        def broken_walk(root, **kwargs):
            kwargs['onerror'](PermissionError(13, 'denied', str(root / 'blocked')))
            return iter(())
        with patch.object(reconcile.os, 'walk', broken_walk):
            report = self.collect()
        self.assertEqual(report['status'], 'attention')
        self.assertEqual(len(report['scan_errors']), 1)
