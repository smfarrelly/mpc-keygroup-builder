import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

from mpc_keygroup_builder.colocated_colors import PAD_BLOCK, colorize_colocated
from mpc_keygroup_builder.programs import load_palette, main


def xml(with_colors=True):
    settings = {'ProgramPads': {'Universal': {'value0': True}, 'Type': {'value0': 1},
                               'pads': {f'value{i}': 123 for i in range(128)}}}
    block = '<ProgramPads>' + json.dumps(settings) + '</ProgramPads>' if with_colors else ''
    return ('<?xml version="1.0" encoding="UTF-8"?>\r\n<MPCVObject><Program type="Drum">'
            '<ProgramName>Original</ProgramName><!-- retained -->'
            '<ProgramPads-v2.10>untouched</ProgramPads-v2.10>' + block +
            '<Instruments><Instrument number="1"><Layers><Layer>'
            '<SampleName>BD Tape</SampleName><SampleFile />'
            '</Layer></Layers></Instrument></Instruments>'
            '<Unknown vendor="x">retain me</Unknown></Program></MPCVObject>').encode()


class ColocatedColorsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'Kit.xpm'
        self.output = self.root / 'Kit FG COLORS.xpm'
        self.source.write_bytes(xml())

    def run_color(self, **kwargs):
        return colorize_colocated(self.source, self.output, load_palette(), **kwargs)

    def test_preserves_every_non_color_byte_and_empty_sample_fields(self):
        before = self.source.read_bytes()
        self.assertEqual(self.run_color(), {'kick': 1})
        result = self.output.read_bytes()
        self.assertEqual(PAD_BLOCK.sub(b'', result), PAD_BLOCK.sub(b'', before))
        self.assertEqual(self.source.read_bytes(), before)
        self.assertIn(b'<SampleFile />', result)
        settings = json.loads(ET.fromstring(result).findtext('Program/ProgramPads'))
        self.assertEqual(settings['ProgramPads']['pads']['value0'], 0xff0000)

    def test_template_adds_map_without_copying_instruments_or_empty_pad_colors(self):
        self.source.write_bytes(xml(False))
        template = self.root / 'Template.xpm'
        template.write_bytes(xml())
        self.run_color(color_template=template)
        self.assertEqual(PAD_BLOCK.sub(b'', self.output.read_bytes()), self.source.read_bytes())
        settings = json.loads(ET.parse(self.output).findtext('Program/ProgramPads'))
        self.assertEqual(settings['ProgramPads']['pads']['value1'], 0)

    def test_missing_map_requires_template_without_output(self):
        self.source.write_bytes(xml(False))
        with self.assertRaisesRegex(ValueError, 'color-template'):
            self.run_color()
        self.assertFalse(self.output.exists())

    def test_no_writes_for_dry_run(self):
        self.run_color(dry_run=True)
        self.assertEqual(list(self.root.iterdir()), [self.source])

    def test_rejects_relocation(self):
        with self.assertRaisesRegex(ValueError, 'beside'):
            colorize_colocated(self.source, self.root / 'elsewhere' / 'Kit.xpm', load_palette())
        self.assertFalse((self.root / 'elsewhere').exists())

    def test_refuses_existing_and_in_place_output(self):
        self.output.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):
            self.run_color()
        self.assertEqual(self.output.read_bytes(), b'keep')
        with self.assertRaises(FileExistsError):
            colorize_colocated(self.source, self.source, load_palette())

    def test_refuses_symlink_output(self):
        self.output.symlink_to(self.root / 'missing.xpm')
        with self.assertRaises(FileExistsError):
            self.run_color()

    def test_refuses_compressed_and_keygroup_sources(self):
        self.source.write_bytes(b'\x1f\x8bgarbage')
        with self.assertRaisesRegex(ValueError, 'XML Drum'):
            self.run_color()
        self.source.write_bytes(xml().replace(b'type="Drum"', b'type="Keygroup"'))
        with self.assertRaisesRegex(ValueError, 'XML Drum'):
            self.run_color()

    def test_refuses_duplicate_color_blocks(self):
        self.source.write_bytes(xml().replace(b'</Program>', b'<ProgramPads>{}</ProgramPads></Program>'))
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            self.run_color()

    def test_failed_write_does_not_leave_output(self):
        with patch('mpc_keygroup_builder.colocated_colors.os.fsync', side_effect=OSError('disk error')):
            with self.assertRaises(OSError):
                self.run_color()
        self.assertFalse(self.output.exists())

    def test_cli_default_filename_and_preview(self):
        with patch('sys.argv', ['mpc-program-color', str(self.source), '--colocated', '--dry-run']):
            self.assertEqual(main(), 0)
        self.assertFalse(self.output.exists())
        with patch('sys.argv', ['mpc-program-color', str(self.source), '--colocated']):
            self.assertEqual(main(), 0)
        self.assertTrue(self.output.exists())
