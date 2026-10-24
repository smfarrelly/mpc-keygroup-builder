"""Static HTML safety/accessibility contracts, not a browser runtime claim."""

from html.parser import HTMLParser
import unittest

from mpc_keygroup_builder.archive_browser import render as archive_html
from mpc_keygroup_builder.home import collect, render as home_html


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def contrast(left, right):
    def luminance(color):
        channels = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
        return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    a, b = sorted((luminance(left), luminance(right)))
    return (b + 0.05) / (a + 0.05)


class BrowserContractTests(unittest.TestCase):
    def pages(self):
        yield home_html(collect())
        yield archive_html({'matches': [], 'archives_scanned': 0, 'invalid_archives': 0,
                            'query': '', 'scan_errors': [], 'skipped_symlinks': []})

    def test_language_viewport_landmark_and_single_title(self):
        for html in self.pages():
            doc = Document()
            doc.feed(html)
            self.assertEqual([attrs['lang'] for tag, attrs in doc.tags if tag == 'html'], ['en'])
            self.assertEqual(sum(tag == 'h1' for tag, _ in doc.tags), 1)
            self.assertEqual(sum(tag == 'main' for tag, _ in doc.tags), 1)
            self.assertTrue(any(tag == 'meta' and attrs.get('name') == 'viewport' for tag, attrs in doc.tags))

    def test_no_external_assets_or_inline_event_handlers(self):
        for html in self.pages():
            doc = Document()
            doc.feed(html)
            for tag, attrs in doc.tags:
                self.assertFalse(any(name.startswith('on') for name in attrs))
                self.assertNotIn('src', attrs)
                if 'href' in attrs:
                    self.assertTrue(attrs['href'].startswith('#'))
            self.assertIn("default-src 'none'", html)

    def test_selected_palette_pairs_clear_contrast_floor(self):
        # A regression floor for these colors, not full accessibility certification.
        for foreground, background in (('#edf7f0', '#111815'), ('#bddbc7', '#1b2820'),
                                       ('#aee6bf', '#111815'), ('#eef7f1', '#18221c'),
                                       ('#c2d3c8', '#111815'), ('#e5bd77', '#24251f')):
            self.assertGreaterEqual(contrast(foreground, background), 4.5)

    def test_archive_notes_and_paths_cannot_create_active_markup(self):
        attack = '</style><img src="https://example.invalid/private" onerror="alert(1)">'
        html = archive_html({'matches': [{'path': '/local/' + attack, 'status': 'invalid', 'error': attack}],
                             'archives_scanned': 1, 'invalid_archives': 1, 'query': attack,
                             'scan_errors': [{'path': attack, 'error': attack}], 'skipped_symlinks': [attack]})
        doc = Document()
        doc.feed(html)
        self.assertFalse(any(tag == 'img' for tag, _ in doc.tags))
        self.assertIn('&lt;img', html)
