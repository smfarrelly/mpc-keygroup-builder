import contextlib
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mpc_keygroup_builder import program_io, model, xpm
from mpc_keygroup_builder.entrypoints import invoke
from mpc_keygroup_builder.readiness import check


class ProgramIoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'program.xpm'

    def compressed(self, document):
        payload = b'ACVS\n3.9\njson\n' + json.dumps(document).encode()
        self.path.write_bytes(gzip.compress(payload))

    def test_source_byte_limit_is_enforced_before_parsing(self):
        self.path.write_bytes(b'x' * 65)
        with patch.object(program_io, 'MAX_SOURCE_BYTES', 64):
            for reader in (model.from_xpm, xpm.inspect, xpm.load_normalized, xpm.load_semantic):
                with self.subTest(reader=reader), self.assertRaisesRegex(ValueError, 'source bytes'):
                    reader(self.path)

    def test_compressed_expansion_is_bounded(self):
        self.path.write_bytes(gzip.compress(b'x' * 4096))
        with patch.object(program_io, 'MAX_EXPANDED_BYTES', 64):
            with self.assertRaisesRegex(ValueError, 'expanded bytes'):
                model.from_xpm(self.path)

    def test_truncated_compression_has_actionable_public_cli_error(self):
        self.path.write_bytes(b'\x1f\x8b\x08\x00')
        with contextlib.redirect_stderr(io.StringIO()) as stream:
            status = invoke('mpc-xpm', ['inspect', str(self.path)])
        self.assertEqual(status, 2)
        self.assertIn('truncated compressed XPM', stream.getvalue())
        self.assertNotIn('Traceback', stream.getvalue())

    def test_xml_depth_elements_and_doctype_are_rejected(self):
        fixtures = [b'<x>' * 130 + b'</x>' * 130,
                    b'<!DOCTYPE x [<!ENTITY a "expanded">]><x>&a;</x>']
        for payload in fixtures:
            with self.subTest(payload=payload[:30]), self.assertRaises(ValueError):
                program_io.xml_root(payload)
        with patch.object(program_io, 'MAX_XML_ELEMENTS', 2), self.assertRaises(ValueError):
            program_io.xml_root(b'<x><a/><b/></x>')

    def test_utf16_doctype_is_also_rejected(self):
        payload = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE x [<!ENTITY a "expanded">]><x>&a;</x>'.encode('utf-16')
        with self.assertRaisesRegex(ValueError, 'document types'):
            program_io.xml_root(payload)

    def test_json_depth_and_duplicate_fields_are_rejected(self):
        for raw in ('[' * 2000 + '0' + ']' * 2000, '{"data":{},"data":{}}'):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                program_io.parse_json(raw)
        with patch.object(program_io, 'MAX_JSON_VALUES', 3), self.assertRaisesRegex(ValueError, 'value inspection'):
            program_io.parse_json('{"a":[1,2]}')

    def test_bad_serialized_shapes_fail_without_attribute_errors(self):
        for data in (None, [], {'drum': []}, {'drum': {'instruments': None}},
                     {'drum': {'instruments': [{'layersv': 7}]}}, {'type': []}):
            self.compressed({'data': data})
            for reader in (model.from_xpm, xpm.inspect):
                with self.subTest(data=data, reader=reader), self.assertRaises(ValueError):
                    reader(self.path)

    def test_bad_pad_structure_has_readable_error(self):
        self.compressed({'data': {'type': 0, 'programPads': {'ProgramPads': None}}})
        with self.assertRaisesRegex(ValueError, 'ProgramPads'):
            xpm.inspect(self.path)

    def test_bad_input_does_not_hide_other_readiness_results(self):
        self.path.write_bytes(gzip.compress(b'x' * 4096))
        other = self.root / 'other.xpm'
        other.write_text('<MPCVObject><Program type="Drum"><ProgramName>Empty</ProgramName></Program></MPCVObject>')
        with patch.object(program_io, 'MAX_EXPANDED_BYTES', 64):
            report = check(programs=[self.path, other])
        self.assertEqual(len(report['checks']), 2)
        self.assertIn('expanded bytes', report['checks'][0]['error'])
        self.assertIn('no populated', report['checks'][1]['detail']['errors'][0])

    def test_directory_input_is_refused_without_reading(self):
        with self.assertRaisesRegex(ValueError, 'regular file'):
            program_io.read_payload(self.root)
