import copy
import json
from html.parser import HTMLParser
from pathlib import Path
import unittest

from mpc_keygroup_builder import capture_guide, xpj


class SavedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.target = "Keys (Macro 1)"
        self.row = {"name": self.target, "target_count": 1, "track": "Keys", "parameter": 4104}
        self.source = {"learned_rows": [self.row]}
        self.track = {"plugin": "Synth", "track": "Keys", "preset": "<Patch>", "preset_edited": False}
        self.audit = {"plugin_tracks": [self.track]}
        self.control = {"name": "Macro 1", "mpc_parameter": 4104, "q_links": ["Screen Q-Link 13"]}
        self.catalog = {"plugins": [{"plugin": "Synth", "controls": [self.control]}]}

    def enrich(self):
        return capture_guide.enrich_control(self.source, self.target, self.audit, self.catalog)

    def test_joins_only_saved_id_name_and_identity(self):
        self.assertEqual(self.enrich()["q_links"], ["Screen Q-Link 13"])
        self.assertEqual(self.enrich()["preset"], "<Patch>")
        self.control["mpc_parameter"] = 4105
        self.assertEqual(self.enrich()["q_links"], [])
        self.control["mpc_parameter"] = 4104
        self.control["name"] = "Unrelated"
        self.assertEqual(self.enrich()["status"], "catalog-unmatched")
        self.control["aliases"] = ["Macro 1"]
        self.assertEqual(self.enrich()["status"], "skin-match")
        self.catalog["plugins"][0]["plugin"] = "Another Synth"
        self.assertEqual(self.enrich()["status"], "catalog-unavailable")
        self.assertEqual(self.enrich()["parameter"], 4104)

    def test_string_alias_or_malformed_learn_rows_cannot_supply_evidence(self):
        self.control.update(name="Other", aliases="Macro 1")
        with self.assertRaisesRegex(ValueError, "aliases"):
            self.enrich()
        self.source["learned_rows"] = [None]
        with self.assertRaisesRegex(ValueError, "learned_rows"):
            self.enrich()

    def test_ambiguities_are_visible(self):
        self.catalog["plugins"][0]["controls"].append(copy.copy(self.control))
        self.assertEqual(self.enrich()["status"], "catalog-ambiguous")
        self.audit["plugin_tracks"].append(self.track)
        self.assertEqual(self.enrich()["status"], "unresolved-track")
        self.row["target_count"] = 2
        self.assertEqual(self.enrich()["status"], "ambiguous-target")
        self.source.clear()
        self.assertEqual(self.enrich()["status"], "older-audit")

    def test_presets_do_not_export_state(self):
        data = {"tracks": [None, {"name": "Drums"}, {"name": "Keys", "program": {"plugin": {"plugin": {
            "state": "PRIVATE", "description": {"name": "Synth", "private": "PRIVATE"},
            "presetName": "<Patch>", "presetEdited": False}}}}]}
        project = xpj.XPJProject(Path("test.xpj"), 3, None, {"data": data})
        self.assertEqual(xpj.plugin_track_rows(project), [self.track])


class GuideParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.assets = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs["href"])
        if "src" in attrs:
            self.assets.append(attrs["src"])

    def handle_data(self, data):
        self.text.append(data)


class BundledGuideTests(unittest.TestCase):
    def test_notes_are_bound_to_project_capture_and_selected_targets(self):
        core = {"id": "core", "capture_name": "Mode", "source_capture": {"sha256": "a" * 64},
                "errors": [], "selected_controls": [{"endpoint": "top-encoder-1",
                    "expected_target": "Synth (Tone)", "channel": 1, "cc": 10,
                    "evidence": {"plugin": "Synth", "preset": "Soft"}}]}
        report = {"cores": [core], "project_name": "Boot.xpj"}
        self.assertIsNone(capture_guide.note_manifest(report))
        report["project_sha256"] = "f" * 64
        first = capture_guide.note_manifest(report)
        self.assertEqual(first["controls"][0]["preset"], "Soft")
        core["selected_controls"][0]["cc"] = 11
        self.assertNotEqual(first["fingerprint"], capture_guide.note_manifest(report)["fingerprint"])
        core["selected_controls"][0]["cc"] = 10
        report["project_sha256"] = "b" * 64
        self.assertNotEqual(first["fingerprint"], capture_guide.note_manifest(report)["fingerprint"])
        core["errors"].append("label changed")
        self.assertIsNone(capture_guide.note_manifest(report))

    def test_two_offline_pages_and_physical_slots(self):
        page = Path(__file__).resolve().parents[1] / "site/saved-xl3-controls.html"
        parser = GuideParser()
        html = page.read_text(encoding="utf-8")
        parser.feed(html)
        self.assertEqual(parser.assets, [])
        payload = html.split('id="note-manifest">', 1)[1].split("</script>", 1)[0]
        manifest = json.loads(payload)
        self.assertEqual(len(manifest["controls"]), 16)
        self.assertEqual({row["preset"] for row in manifest["controls"]}, {"Fat Square", "Tron Guitar"})
        self.assertEqual(len(manifest["project_sha256"]), 64)
        self.assertEqual(parser.links, ["#opx4-macros-core", "#jura-live-core"])
        self.assertEqual(len(set(parser.ids)), len(parser.ids))
        for link in parser.links:
            self.assertIn(link[1:], parser.ids)
        self.assertIn("jura-live-core-upper-button-1", parser.ids)
        self.assertIn("opx4-macros-core-top-encoder-5", parser.ids)
        self.assertEqual(html.count(">No saved Learn target<"), 8)
        self.assertEqual(html.count("Screen Mode T1/S1 Q-Link "), 8)
        self.assertNotIn("/home/", html)
        self.assertNotIn("/media/", html)
