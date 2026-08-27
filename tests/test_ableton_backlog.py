import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import ableton_backlog


class AbletonBacklogTests(unittest.TestCase):
    def test_pack_display_preserves_instrument_acronyms(self):
        self.assertEqual(ableton_backlog.display_pack("sp1200_from_mars"), "SP-1200")
        self.assertEqual(ableton_backlog.display_pack("cr78_from_mars"), "CR-78")
        self.assertEqual(ableton_backlog.display_pack("dx_100_from_mars"), "DX100")
        self.assertEqual(ableton_backlog.display_pack("lo-fi_drum_machines_from_mars"), "Lo-Fi Drum Machines")

    def inventory(self):
        return {
            "root": "/samples",
            "issues": ["one bad preset"],
            "presets": [
                {
                    "path": "vinyl_sp_from_mars/Presets/02. Kits/808 Kit.adg",
                    "name": "808 Kit",
                    "kind": "adg",
                    "zones": 16,
                    "unique_samples": 16,
                    "macros": 7,
                    "warped_zones": {"false": 16},
                    "device_types": {"DrumGroupDevice": 1},
                    "fidelity": {"grade": "C", "label": "template"},
                },
                {
                    "path": "vinyl_breaks_from_mars/Presets/Loops/Break.adg",
                    "name": "Dust Break",
                    "kind": "adg",
                    "zones": 4,
                    "unique_samples": 4,
                    "macros": 1,
                    "warped_zones": {"true": 4},
                    "device_types": {"OriginalSimpler": 1},
                    "fidelity": {"grade": "B", "label": "close"},
                },
                {
                    "path": "vinyl_drums_from_mars/Presets/02. Kits/Big Break Kit.adg",
                    "name": "Big Break Kit",
                    "kind": "adg",
                    "zones": 16,
                    "unique_samples": 16,
                    "macros": 4,
                    "warped_zones": {"false": 16},
                    "device_types": {"DrumGroupDevice": 1},
                    "fidelity": {"grade": "C", "label": "template"},
                },
                {
                    "path": "mirage_from_mars/Ableton/Mirage.als",
                    "name": "Mirage Set",
                    "kind": "als",
                    "zones": 20,
                    "unique_samples": 20,
                    "macros": 2,
                    "warped_zones": {"false": 20},
                    "device_types": {"DrumGroupDevice": 1, "OriginalSimpler": 2},
                    "fidelity": {"grade": "B", "label": "close"},
                },
                {
                    "path": "plugin_pack/Presets/Plugin.adg",
                    "name": "Plugin",
                    "kind": "adg",
                    "zones": 0,
                    "unique_samples": 0,
                    "macros": 0,
                    "warped_zones": {},
                    "device_types": {"PluginDevice": 1},
                    "fidelity": {"grade": "D", "label": "reference-only"},
                },
                {
                    "path": "dx_100_from_mars/Presets/Steel Drums.adg",
                    "name": "Steel Drums",
                    "kind": "adg",
                    "zones": 40,
                    "unique_samples": 40,
                    "macros": 2,
                    "warped_zones": {"false": 40},
                    "device_types": {"OriginalSimpler": 1},
                    "fidelity": {"grade": "B", "label": "close"},
                },
            ],
        }

    def catalog(self):
        return {
            "programs": [
                {
                    "collection": "Vinyl SP From Mars",
                    "category": "Drums",
                    "program_type": "drum",
                },
                {
                    "collection": "Mirage From Mars",
                    "category": "Keys",
                    "program_type": "keygroup",
                },
            ]
        }

    def test_classifies_targets_and_preserves_source_issues(self):
        backlog = ableton_backlog.build_backlog(self.inventory(), self.catalog())
        targets = {entry["name"]: entry["target"] for entry in backlog["entries"]}
        self.assertEqual(targets["808 Kit"], "drum")
        self.assertEqual(targets["Dust Break"], "clip")
        self.assertEqual(targets["Big Break Kit"], "drum")
        self.assertEqual(targets["Mirage Set"], "project")
        self.assertEqual(targets["Plugin"], "reference")
        self.assertEqual(backlog["summary"]["source_issues"], 1)
        self.assertEqual(targets["Steel Drums"], "keygroup")
        self.assertEqual(backlog["summary"]["packs"], 6)

    def test_existing_catalog_coverage_is_attached_and_reduces_score(self):
        without = ableton_backlog.build_backlog(self.inventory())
        with_catalog = ableton_backlog.build_backlog(self.inventory(), self.catalog())
        plain = next(item for item in without["entries"] if item["name"] == "808 Kit")
        covered = next(item for item in with_catalog["entries"] if item["name"] == "808 Kit")
        self.assertEqual(covered["existing_mpc"], {"drum": 1})
        self.assertLess(covered["score"], plain["score"])

    def test_markdown_is_pack_oriented_and_documents_policy(self):
        backlog = ableton_backlog.build_backlog(self.inventory(), self.catalog())
        rendered = ableton_backlog.render_markdown(backlog)
        self.assertIn("Samples From Mars Ableton-to-MPC backlog", rendered)
        self.assertIn("Vinyl SP", rendered)
        self.assertIn("Conversion policy", rendered)
        self.assertIn("complete preset-level queue", rendered)
        self.assertIn("drum=1", rendered)

    def test_exact_duplicate_sources_are_hashed_and_demoted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = "pack/Preset.adg"
            duplicate = "pack(1)/Preset.adg"
            for relative in (first, duplicate):
                path = root / relative
                path.parent.mkdir()
                path.write_bytes(b"same preset")
            inventory = self.inventory()
            inventory["root"] = str(root)
            template = inventory["presets"][0]
            inventory["presets"] = [
                {**template, "path": first, "name": "Canonical"},
                {**template, "path": duplicate, "name": "Duplicate"},
            ]
            backlog = ableton_backlog.build_backlog(inventory)
            duplicate_entry = next(item for item in backlog["entries"] if item["name"] == "Duplicate")
            canonical_entry = next(item for item in backlog["entries"] if item["name"] == "Canonical")
            self.assertEqual(duplicate_entry["duplicate_of"], first)
            self.assertLess(duplicate_entry["score"], canonical_entry["score"])
            self.assertEqual(backlog["summary"]["exact_duplicates"], 1)


if __name__ == "__main__":
    unittest.main()
