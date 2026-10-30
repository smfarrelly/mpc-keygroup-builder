import json
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave

from mpc_keygroup_builder import source_regions
from tests import test_ableton_keygroup_wave as wave_fixtures


class SourceRegionTests(unittest.TestCase):
    def fixture(self, root):
        source = root / 'source'
        preset = wave_fixtures.AbletonKeygroupWaveTests.fixture(source, 'pack', 'Voice')
        report = source_regions.ableton.inspect(preset)
        report['zones'][0].update(samplestart=3, sampleend=8)
        return source, preset, report

    def test_region_excludes_attack_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, preset, report = self.fixture(root)
            wav = source / 'pack/WAV/Voice C1.wav'
            with wave.open(str(wav), 'wb') as stream:
                stream.setparams((1, 2, 44100, 0, 'NONE', 'not compressed'))
                stream.writeframes(struct.pack('<20h', *([12000]*3 + [0]*17)))
            before = wav.read_bytes()
            with patch.object(source_regions.ableton, 'inspect', return_value=report):
                result = source_regions.compare(preset, source, root / 'out')
            self.assertEqual(wav.read_bytes(), before)
            self.assertEqual(result['zones'][0]['start'], 3)
            self.assertEqual(result['zones'][0]['end'], 8)
            with wave.open(str(root/'out/01-region.wav')) as stream:
                self.assertEqual(stream.getnframes(), 6)
                self.assertEqual(stream.readframes(6), bytes(12))
            with wave.open(str(root/'out/01-full.wav')) as stream:
                self.assertNotEqual(stream.readframes(3), bytes(6))
            self.assertIn('not converted instruments', result['limitations'])
            self.assertEqual(json.loads((root/'out/comparison.json').read_text()), result)
            class AudioLinks(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.sources = []
                def handle_starttag(self, tag, attrs):
                    if tag == 'audio':
                        self.sources.append(dict(attrs)['src'])
            page = (root/'out/review.html').read_text()
            links = AudioLinks()
            links.feed(page)
            self.assertEqual(links.sources, ['01-full.wav', '01-region.wav'])
            for name in links.sources:
                self.assertTrue((root/'out'/name).is_file())
            self.assertIn('not an MPC instrument', page)
            with self.assertRaises(FileExistsError):
                source_regions.compare(preset, source, root/'out')

    def test_invalid_region_leaves_no_partial_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, preset, report = self.fixture(root)
            report['zones'][0]['samplestart'] = 999
            with patch.object(source_regions.ableton, 'inspect', return_value=report):
                with self.assertRaisesRegex(ValueError, 'sample bounds'):
                    source_regions.compare(preset, source, root/'out')
            self.assertFalse((root/'out').exists())
            self.assertEqual(list(root.glob('.source-regions-*')), [])

    def test_source_and_output_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, preset, report = self.fixture(root)
            with self.assertRaisesRegex(ValueError, 'outside the source'):
                source_regions.compare(preset, source, source/'new')
            report['zones'][0]['sample']['relative_path'] = '../../outside.wav'
            (root/'outside.wav').touch()
            with patch.object(source_regions.ableton, 'inspect', return_value=report):
                with self.assertRaisesRegex(ValueError, 'escapes'):
                    source_regions.compare(preset, source, root/'out')
            self.assertFalse((root/'out').exists())

    def test_zone_limit_and_inactive_zone_handling(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, preset, report = self.fixture(root)
            zone = report['zones'][0]
            report['zones'] = [zone] * 17
            with patch.object(source_regions.ableton, 'inspect', return_value=report):
                with self.assertRaisesRegex(ValueError, '1..16 active zones'):
                    source_regions.compare(preset, source, root/'out')
            report['zones'] = [zone, {'isactive': False, 'sample': None}]
            with patch.object(source_regions.ableton, 'inspect', return_value=report):
                result = source_regions.compare(preset, source, root/'out')
            self.assertEqual(len(result['zones']), 1)

    def test_source_hash_matches_decoded_snapshot_during_external_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, preset, report = self.fixture(root)
            wav = source/'pack/WAV/Voice C1.wav'
            original = wav.read_bytes()
            decode = source_regions.read_pcm_mono
            def change_after_read(stream):
                wav.write_bytes(original[:-2] + b'\x01\x00')
                return decode(stream)
            with patch.object(source_regions.ableton, 'inspect', return_value=report), \
                 patch.object(source_regions, 'read_pcm_mono', side_effect=change_after_read):
                result = source_regions.compare(preset, source, root/'out')
            self.assertEqual(result['zones'][0]['sample_sha256'], hashlib.sha256(original).hexdigest())
            self.assertNotEqual(wav.read_bytes(), original)

    def test_review_escapes_source_text(self):
        report = {'preset': '<script>alert(1)</script>', 'limitations': 'reference only', 'zones': [{
            'zone': 1, 'sample': '<img src=x onerror=alert(1)>',
            'start': 0, 'end': 1, 'source_frames': 2,
            'full_preview': '01-full.wav', 'region_preview': '01-region.wav',
            'source_settings': {'name': '</pre><script>bad</script>'},
        }]}
        page = source_regions.review_html(report)
        self.assertNotIn('<script>', page)
        self.assertNotIn('<img ', page)
        self.assertIn('&lt;script&gt;', page)

    def test_concurrent_destination_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, preset, report = self.fixture(root)
            publish = source_regions.publish_directory
            def race(stage, destination):
                destination.mkdir()
                (destination/'keep.txt').write_text('keep')
                publish(stage, destination)
            with patch.object(source_regions.ableton, 'inspect', return_value=report), \
                 patch.object(source_regions, 'publish_directory', side_effect=race):
                with self.assertRaises(FileExistsError):
                    source_regions.compare(preset, source, root/'out')
            self.assertEqual((root/'out/keep.txt').read_text(), 'keep')
            self.assertFalse((root/'out/comparison.json').exists())
            self.assertEqual(list(root.glob('.source-regions-*')), [])
