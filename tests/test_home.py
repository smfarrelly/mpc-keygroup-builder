import contextlib
import csv
from html.parser import HTMLParser
import io
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import home
from mpc_keygroup_builder.capture import capture_projects, verify_capture
from mpc_keygroup_builder.entrypoints import invoke


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.scripts = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag == 'a':
            self.links.append(attrs['href'])
        if tag == 'script':
            self.scripts += 1


class HomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ledger = self.root / 'ledger.csv'
        self.output = self.root / 'reports/home.html'
        self.programs = self.root / 'programs'
        self.programs.mkdir()

    def ledger_file(self, path='Kit.xpm', note='Keep this groove'):
        with self.ledger.open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['path', 'program_type', 'hardware_status', 'favorite', 'scratchpad_role', 'notes'])
            writer.writerow([path, 'Drum', 'pass', 'yes', 'Main drums', note])

    def test_empty_page_is_explicit_about_missing_evidence(self):
        home.build(self.output)
        html = self.output.read_text()
        for message in ('No ledger selected', 'No archive library selected', 'No bundles selected'):
            self.assertIn(message, html)
        parser = PageParser()
        parser.feed(html)
        self.assertEqual(parser.scripts, 0)
        self.assertTrue(all(link.startswith('#') and link[1:] in parser.ids for link in parser.links))

    def test_favorite_absolute_location_and_history_are_separate(self):
        self.ledger_file()
        (self.programs / 'Kit.xpm').write_bytes(b'placeholder')
        report = home.build(self.output, ledger=self.ledger, program_root=self.programs)
        row = report['favorites'][0]
        self.assertEqual(row['local_status'], 'found')
        self.assertEqual(row['local_path'], str(self.programs / 'Kit.xpm'))
        self.assertIn('Historical hardware status: pass', self.output.read_text())

    def test_missing_favorite_and_unsafe_paths_need_attention(self):
        for path in ('missing.xpm', '../outside.xpm', '/outside.xpm', 'C:\\kit.xpm'):
            self.ledger_file(path)
            report = home.collect(ledger=self.ledger, program_root=self.programs)
            self.assertEqual(report['status'], 'attention')
            self.assertNotEqual(report['favorites'][0]['local_status'], 'found')

    def test_symlink_escape_does_not_expose_target_path(self):
        outside = self.root / 'outside.xpm'
        outside.write_bytes(b'private')
        (self.programs / 'alias.xpm').symlink_to(outside)
        self.ledger_file('alias.xpm')
        row = home.collect(ledger=self.ledger, program_root=self.programs)['favorites'][0]
        self.assertEqual(row['local_status'], 'outside-root')
        self.assertEqual(row['local_path'], '')

    def test_notes_cannot_inject_markup(self):
        self.ledger_file(note='<script>alert("x")</script>')
        home.build(self.output, ledger=self.ledger)
        html = self.output.read_text()
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)

    def test_output_cannot_modify_inputs_or_overwrite_existing_files(self):
        with self.assertRaises(ValueError):
            home.build(self.programs / 'home.html', ledger=self.ledger, program_root=self.programs)
        home.build(self.output)
        original = self.output.read_bytes()
        with self.assertRaises(FileExistsError):
            home.build(self.output)
        self.assertEqual(self.output.read_bytes(), original)
        link = self.root / 'alias.html'
        link.symlink_to(self.root / 'missing.html')
        with self.assertRaises(FileExistsError):
            home.build(link)

    def test_archive_integrity_preserved_and_damage_visible(self):
        source = self.root / 'source'
        source.mkdir()
        (source / 'Idea.xpj').write_bytes(b'project')
        (source / 'Idea_[ProjectData]').mkdir()
        library = self.root / 'ideas'
        archive = library / 'take'
        capture_projects(source, archive, ('Idea.xpj',), note='Keep the bass')
        home.build(self.output, archive_library=library)
        self.assertIn('Keep the bass', self.output.read_text())
        self.assertEqual(verify_capture(archive)['status'], 'verified')
        (archive / 'Idea.xpj').write_bytes(b'changed')
        self.assertEqual(home.collect(archive_library=library)['status'], 'attention')

    def test_missing_bundle_is_visible(self):
        report = home.build(self.output, bundles=[self.root / 'missing'])
        self.assertEqual(report['status'], 'attention')
        self.assertIn('fail', self.output.read_text())

    def candidate_program(self, name='Collection/Kit.xpm', sample=True):
        path = self.programs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('<MPCVObject><Program type="Drum"><ProgramName>Kit</ProgramName><Instruments><Instrument number="1"><Layers><Layer><SampleFile>kick.wav</SampleFile></Layer></Layers></Instrument></Instruments></Program></MPCVObject>')
        if sample:
            (path.parent / 'kick.wav').write_bytes(b'fixture')
        return path

    def test_different_layout_candidates_and_sample_evidence(self):
        self.ledger_file('Programs/Collection/Kit.xpm')
        path = self.candidate_program()
        report = home.build(self.output, ledger=self.ledger, library_roots=[self.programs], verify_samples=True)
        self.assertEqual(report['status'], 'pass')
        self.assertEqual(report['favorites'][0]['local_status'], 'not-checked')
        candidate = report['reconciliation']['rows'][0]['candidates'][0]
        self.assertEqual(candidate['sample_status'], 'pass')
        html = self.output.read_text()
        for text in (str(path), 'Local location matching: candidate', 'Historical hardware status: pass',
                     'Recorded library / SD navigation path', 'not proven identical', 'Sample-reference checks do not decode audio'):
            self.assertIn(text, html)

    def test_sample_failure_remains_attention_with_found_candidate(self):
        self.ledger_file('Programs/Collection/Kit.xpm')
        self.candidate_program(sample=False)
        report = home.build(self.output, ledger=self.ledger, library_roots=[self.programs], verify_samples=True)
        self.assertEqual(report['status'], 'attention')
        self.assertIn('sample references: fail', self.output.read_text())

    def test_recorded_layout_sample_check_is_opt_in(self):
        self.ledger_file('Collection/Kit.xpm')
        self.candidate_program(sample=False)
        report = home.collect(ledger=self.ledger, program_root=self.programs)
        self.assertEqual(report['favorites'][0]['sample_status'], 'not-checked')
        report = home.collect(ledger=self.ledger, program_root=self.programs, verify_samples=True)
        self.assertEqual(report['status'], 'attention')
        self.assertEqual(report['favorites'][0]['sample_status'], 'fail')

    def test_ambiguous_candidates_are_all_shown_without_a_selected_winner(self):
        self.ledger_file('Programs/Collection/Kit.xpm')
        one = self.candidate_program()
        two = self.candidate_program('Other/Kit.xpm')
        report = home.build(self.output, ledger=self.ledger, library_roots=[self.programs])
        self.assertEqual(report['status'], 'attention')
        html = self.output.read_text()
        self.assertIn(str(one), html)
        self.assertIn(str(two), html)
        self.assertIn('Local location matching: ambiguous', html)

    def test_library_output_and_unused_options_are_rejected(self):
        self.ledger_file()
        with self.assertRaises(ValueError):
            home.build(self.programs / 'report.html', ledger=self.ledger, library_roots=[self.programs])
        for options in ({'library_roots': [self.programs]}, {'verify_samples': True},
                        {'ledger': self.ledger, 'verify_samples': True}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                home.build(self.output, **options)
        self.assertFalse(self.output.exists())

    def test_candidate_names_are_escaped_and_commands_are_shell_quoted(self):
        name = "Collection/Kit <&> ' name.xpm"
        self.ledger_file('Programs/' + name)
        self.candidate_program(name)
        home.build(self.output, ledger=self.ledger, library_roots=[self.programs])
        html = self.output.read_text()
        self.assertNotIn('<&>', html)
        self.assertIn('&lt;&amp;&gt;', html)
        self.assertIn('mpc-tools check --program', html)

    def test_page_prioritizes_personal_sounds_over_generic_commands(self):
        home.build(self.output)
        html = self.output.read_text()
        self.assertLess(html.index('<section id="favorites">'), html.index('<section id="workflows">'))

    def test_home_public_cli_reconciles_explicit_library(self):
        self.ledger_file('Programs/Collection/Kit.xpm')
        self.candidate_program()
        with contextlib.redirect_stdout(io.StringIO()):
            code = invoke('mpc-tools', ['home', '--ledger', str(self.ledger), '--library-root', str(self.programs), '--verify-samples', '--output', str(self.output)])
        self.assertEqual(code, 0)
        self.assertIn('sample references: pass', self.output.read_text())

    def test_invalid_arguments_fail_before_creating_output(self):
        for inputs in ({'program_root': self.programs}, {'recipe_root': self.root}, {'ledger': self.ledger}):
            with self.assertRaises((ValueError, FileNotFoundError)):
                home.build(self.output, **inputs)
            self.assertFalse(self.output.parent.exists())

    def test_public_cli_returns_attention_but_still_writes_report(self):
        with contextlib.redirect_stdout(io.StringIO()):
            status = invoke('mpc-tools', ['home', '--output', str(self.output), '--bundle', str(self.root / 'missing')])
        self.assertEqual(status, 1)
        self.assertTrue(self.output.is_file())
