import csv
import json
import struct
import tempfile
import unittest
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

from mpc_keygroup_builder.catalog import build_catalog, query_catalog


class CatalogTests(unittest.TestCase):
    def _program(self, path: Path, sample: str = "BD Warm.wav") -> None:
        path.parent.mkdir(parents=True)
        root = ET.Element("MPCVObject")
        program = ET.SubElement(root, "Program", type="Drum")
        ET.SubElement(program, "ProgramName").text = "Catalog Kit"
        pads = {
            "ProgramPads": {
                "Universal": {"value0": False},
                "Type": {"value0": 2},
                "pads": {"value0": 0xFF0000},
            }
        }
        ET.SubElement(program, "ProgramPads").text = json.dumps(pads)
        instruments = ET.SubElement(program, "Instruments")
        instrument = ET.SubElement(instruments, "Instrument", number="1")
        layers = ET.SubElement(instrument, "Layers")
        layer = ET.SubElement(layers, "Layer")
        ET.SubElement(layer, "SampleFile").text = sample
        ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)

    def _ledger(self, path: Path) -> None:
        fields = [
            "path",
            "program_type",
            "format",
            "structural_status",
            "semantic_verdict",
            "hardware_status",
            "favorite",
            "scratchpad_role",
            "notes",
        ]
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerow(
                {
                    "path": "Programs/Keygroups/Samples From Mars/Pack/Drums/Kit.xpm",
                    "program_type": "Drum",
                    "format": "xml",
                    "structural_status": "pass",
                    "semantic_verdict": "pass",
                    "hardware_status": "pass",
                    "favorite": "yes",
                    "scratchpad_role": "main drums",
                    "notes": "favorite kit",
                }
            )
            writer.writerow(
                {
                    "path": "Programs/Keygroups/Samples From Mars/Pack/Bass/Missing.xpm",
                    "program_type": "Keygroup",
                    "format": "gzip-json",
                    "hardware_status": "untested",
                }
            )
            writer.writerow(
                {
                    "path": "../Escaped.xpm",
                    "program_type": "Drum",
                    "format": "xml",
                    "hardware_status": "untested",
                }
            )

    def _impulse(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        values = [28000] * 100 + [0] * 4310
        with wave.open(str(path), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(44100)
            stream.writeframes(b"".join(struct.pack("<h", value) for value in values))

    def test_builds_metadata_only_catalog_and_queries_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "ledger.csv"
            self._ledger(ledger)
            self._program(
                root / "Programs/Keygroups/Samples From Mars/Pack/Drums/Kit.xpm"
            )
            catalog = build_catalog(ledger, root)
            self.assertEqual(catalog["summary"]["programs"], 3)
            self.assertEqual(
                catalog["summary"]["index_status"],
                {"error": 1, "missing": 1, "pass": 1},
            )
            kit = catalog["programs"][0]
            self.assertEqual(kit["collection"], "Pack")
            self.assertEqual(kit["semantic_roles"], {"kick.primary": 1})
            self.assertEqual(kit["populated_banks"], ["A"])
            self.assertEqual(query_catalog(catalog, role="kick"), [kit])
            self.assertEqual(query_catalog(catalog, favorite="yes"), [kit])
            self.assertEqual(query_catalog(catalog, search="favorite"), [kit])
            self.assertEqual(
                catalog["programs"][2]["index_error"],
                "ledger path escapes the program root",
            )

    def test_audio_facets_are_optional_queryable_and_keep_resolved_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "ledger.csv"
            self._ledger(ledger)
            program = root / "Programs/Keygroups/Samples From Mars/Pack/Drums/Kit.xpm"
            self._program(program)
            self._impulse(program.with_name("Kit_[ProgramData]") / "BD Warm.wav")
            catalog = build_catalog(ledger, root, include_audio=True)
            kit = catalog["programs"][0]
            facets = kit["audio_facets"]
            self.assertEqual(facets["status"], "pass")
            self.assertEqual(facets["measured_samples"], 1)
            self.assertEqual(facets["descriptors"]["duration"], {"short": 1})
            self.assertEqual(facets["descriptors"]["transient"], {"sharp": 1})
            self.assertEqual(
                facets["samples"][0]["path"],
                "Programs/Keygroups/Samples From Mars/Pack/Drums/Kit_[ProgramData]/BD Warm.wav",
            )
            self.assertEqual(query_catalog(catalog, duration="short", transient="sharp"), [kit])
            self.assertEqual(query_catalog(catalog, duration="long"), [])

    def test_audio_facets_resolve_mpc_sample_stems_to_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "ledger.csv"
            self._ledger(ledger)
            program = root / "Programs/Keygroups/Samples From Mars/Pack/Drums/Kit.xpm"
            self._program(program, sample="BD Warm")
            self._impulse(program.parent / "BD Warm.wav")
            catalog = build_catalog(ledger, root, include_audio=True)
            facets = catalog["programs"][0]["audio_facets"]
            self.assertEqual(facets["status"], "pass")
            self.assertEqual(facets["measured_samples"], 1)

    def test_note_range_filters_support_both_bounds(self):
        catalog = {
            "programs": [
                {"name": "Narrow", "note_range": {"low": 36, "high": 84}},
                {"name": "Wide", "note_range": {"low": 0, "high": 127}},
                {"name": "Drum", "note_range": None},
            ]
        }
        self.assertEqual(
            [item["name"] for item in query_catalog(catalog, note_low_at_least=24, note_high_at_most=96)],
            ["Narrow"],
        )
        self.assertEqual(
            [item["name"] for item in query_catalog(catalog, note_low_at_most=0, note_high_at_least=127)],
            ["Wide"],
        )


if __name__ == "__main__":
    unittest.main()
