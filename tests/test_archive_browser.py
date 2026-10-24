import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder.archive_browser import render, write
from mpc_keygroup_builder.capture import capture_projects, verify_capture
from mpc_keygroup_builder.entrypoints import invoke
from mpc_keygroup_builder.idea_archive import list_archives


class ArchiveBrowserTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'Idea.xpj').write_bytes(b'project')
        (self.source / 'Idea_[ProjectData]').mkdir()
        self.library = self.root / 'library'
        self.archive = self.library / 'take'
        capture_projects(self.source, self.archive, ('Idea.xpj',), note='<script>alert("note")</script>')

    def test_untrusted_notes_are_text_not_markup(self):
        html = render(list_archives(self.library))
        self.assertIn('&lt;script&gt;alert', html)
        self.assertNotIn('<script>alert', html)
        self.assertIn("connect-src 'none'", html)
        self.assertIn('not a live connection', html)
        self.assertNotIn('fetch(', html)

    def test_report_cannot_replace_files_or_live_inside_library(self):
        report = list_archives(self.library)
        with self.assertRaises(ValueError):
            write(report, self.archive / 'index.html', self.library)
        output = self.root / 'report.html'
        write(report, output, self.library)
        original = output.read_bytes()
        with self.assertRaises(FileExistsError):
            write(report, output, self.library)
        self.assertEqual(output.read_bytes(), original)
        self.assertEqual(verify_capture(self.archive)['status'], 'verified')

    def test_symlink_output_rejected(self):
        link = self.root / 'link.html'
        link.symlink_to(self.root / 'missing.html')
        with self.assertRaises(FileExistsError):
            write(list_archives(self.library), link, self.library)

    def test_cli_exports_report_and_preserves_json(self):
        output = self.root / 'reports' / 'ideas.html'
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            status = invoke('mpc-idea-archive', ['list', str(self.library), '--html', str(output), '--json'])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(printed.getvalue())['html_report'], str(output))
        self.assertTrue(output.is_file())

    def test_filtered_invalid_archive_remains_in_overall_count(self):
        (self.archive / 'Idea.xpj').write_bytes(b'bad')
        output = self.root / 'report.html'
        with contextlib.redirect_stdout(io.StringIO()):
            status = invoke('mpc-idea-archive', ['list', str(self.library), '--query', 'no-match', '--html', str(output)])
        self.assertEqual(status, 1)
        self.assertIn('1 invalid across the full scan', output.read_text())
        self.assertIn('0 archive cards', output.read_text())

    def test_invalid_project_metadata_is_reported_without_crashing_render(self):
        manifest_path = self.archive / 'capture-manifest.json'
        manifest = json.loads(manifest_path.read_text())
        for projects in (None, 'not-a-list', [42], {'name': 'Idea.xpj'}):
            manifest['projects'] = projects
            manifest_path.write_text(json.dumps(manifest))
            report = list_archives(self.library)
            self.assertEqual(report['invalid_archives'], 1)
            self.assertIn('projects must be a list of strings', render(report))
