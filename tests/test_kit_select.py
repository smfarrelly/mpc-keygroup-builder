import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder.kit_select import (
    load_recipe,
    render_manifest,
    render_markdown,
    select_kit,
    stage_audio,
)
from mpc_keygroup_builder.model import from_drum_manifest


class KitSelectTests(unittest.TestCase):
    def _recipe(self, root: Path) -> Path:
        path = root / "kit.toml"
        path.write_text(
            'schema_version=1\nid="cross"\nname="Cross Kit"\nseed=7\n'
            '[[pads]]\npad=1\nrole="kick"\nprefer_duration="short"\nprefer_transient="sharp"\n'
            '[[pads]]\npad=2\nrole="snare"\nprefer_loudness="moderate"\n',
            encoding="utf-8",
        )
        return path

    def _catalog(self, root: Path) -> dict:
        def program(collection, name, role, sample, descriptors, favorite=""):
            relative = f"Audio/{collection}/{name}/{sample}"
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture")
            return {
                "path": f"Programs/{collection}/{name}.xpm",
                "name": name,
                "collection": collection,
                "program_type": "drum",
                "index_status": "pass",
                "hardware_status": "pass",
                "favorite": favorite,
                "zones": [{"index": 1, "role": role, "samples": [sample]}],
                "audio_facets": {
                    "samples": [{
                        "sample": sample,
                        "path": relative,
                        "duration_seconds": 0.2,
                        "rms_dbfs": -18.0,
                        "peak_dbfs": -2.0,
                        "crest_db": 16.0,
                        "attack_milliseconds": 2.0,
                        "onset_to_body_db": 4.0,
                        "descriptors": descriptors,
                    }]
                },
            }
        return {
            "schema_version": 1,
            "program_root": str(root),
            "audio_facets_enabled": True,
            "programs": [
                program("Pack A", "Kit A", "kick.primary", "Kick A.wav", {
                    "duration": "short", "loudness": "moderate", "transient": "sharp"
                }, "yes"),
                program("Pack B", "Kit B", "kick.primary", "Kick B.wav", {
                    "duration": "medium", "loudness": "loud", "transient": "soft"
                }),
                program("Pack C", "Kit C", "snare.primary", "Snare C.wav", {
                    "duration": "short", "loudness": "moderate", "transient": "defined"
                }),
            ],
        }

    def test_selects_deterministically_with_provenance_and_buildable_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe = load_recipe(self._recipe(root))
            catalog = self._catalog(root)
            first = select_kit(recipe, catalog, catalog_path=root / "catalog.json")
            second = select_kit(recipe, catalog, catalog_path=root / "catalog.json")
            self.assertEqual(first, second)
            self.assertEqual([item.pad for item in first.selections], [1, 2])
            self.assertEqual(first.selections[0].source_program_name, "Kit A")
            self.assertEqual(first.selections[0].preference_matches, ("duration", "transient"))
            self.assertEqual({item.collection for item in first.selections}, {"Pack A", "Pack C"})
            manifest = root / "selected.toml"
            manifest.write_text(render_manifest(first), encoding="utf-8")
            staging = root / "staged"
            report = stage_audio(first, staging)
            self.assertEqual(report["files"], 2)
            self.assertTrue(all(len(item["sha256"]) == 64 for item in report["copies"]))
            model = from_drum_manifest(manifest, staging)
            self.assertEqual(model.name, "Cross Kit")
            self.assertEqual([zone.role for zone in model.zones], ["kick.primary", "snare.primary"])
            markdown = render_markdown(first)
            self.assertIn("Licensed audio remains in its source library", markdown)
            self.assertIn("--source-root", markdown)

    def test_requires_enriched_catalog_and_reports_missing_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe = load_recipe(self._recipe(root))
            catalog = self._catalog(root)
            catalog["audio_facets_enabled"] = False
            with self.assertRaisesRegex(ValueError, "--audio-facets"):
                select_kit(recipe, catalog, catalog_path=root / "catalog.json")
            catalog["audio_facets_enabled"] = True
            catalog["programs"] = [item for item in catalog["programs"] if "Snare" not in str(item)]
            with self.assertRaisesRegex(ValueError, "role snare"):
                select_kit(recipe, catalog, catalog_path=root / "catalog.json")

    def test_recipe_validation_rejects_duplicate_pads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self._recipe(root)
            text = path.read_text(encoding="utf-8").replace("pad=2", "pad=1")
            path.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unique"):
                load_recipe(path)


if __name__ == "__main__":
    unittest.main()
