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
