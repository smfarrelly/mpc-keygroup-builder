import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from mpc_keygroup_builder import plugin_companion, plugin_core, plugin_map, plugin_params, plugin_seed, sdk_params

ROOT = Path(__file__).resolve().parents[1]
DUMP = ROOT / "tests/fixtures/sdk/stereo-delay.json"
PROFILE = ROOT / "midi/sdk-examples/stereo-delay.toml"


class SDKParametersTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dump = sdk_params.read_dump(DUMP)
        self.profile = plugin_map.load_profile(PROFILE)

    def save(self, dump):
        path = self.root / "params.json"
        path.write_text(json.dumps(dump), encoding="utf-8")
        return path

    def test_real_dump_compiles_four_encoder_worksheet_and_companion(self):
        catalog = plugin_params.catalog(DUMP)
        plugin = catalog["plugins"][0]
        self.assertEqual(plugin["control_count"], 8)
        self.assertEqual(plugin["learned_control_count"], 0)
        feedback = plugin_params.filtered(catalog, "feedback", False, 1)[0]
        self.assertEqual(feedback["sdk"]["label"], "%")
        self.assertIsNone(feedback["mpc_parameter"])
        self.assertEqual(feedback["sdk"]["default"], 0.4)
        self.assertIn("Choices: 1/64", plugin_params.render_markdown(catalog, plugin["controls"]))
        out = self.root / "packet"
        plugin_map.compile_batch([self.profile], catalog, out)
        import csv
        with (out / "mpc-midi-learn-all.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([r["cc"] for r in rows], ["20", "21", "22", "23"])
        self.assertTrue(all(r["mpc_parameter"] == "" and r["hardware_status"] == "pending" for r in rows))
        self.assertNotIn("+4096", (out / "HARDWARE_CHECKLIST.md").read_text())
        page = plugin_companion.companion_data([self.profile], catalog)
        self.assertEqual(page["pages"][0]["controls"][0]["sdk"]["choices"][0], "1/64")
        self.assertIn("Feedback", plugin_companion.render_html(page))

    def test_drift_or_wrong_identity_blocks_profile(self):
        for key, value in [("uidInt", 123), ("vendor", "Different vendor")]:
            with self.subTest(key=key):
                catalog = plugin_params.catalog(self.save({**self.dump, key: value}))
                self.assertTrue(plugin_map.validate_profile(self.profile, catalog)["errors"])
        for key, value in [("name", "New control"), ("automatable", False)]:
            changed = copy.deepcopy(self.dump)
            changed["params"][7][key] = value
            catalog = plugin_params.catalog(self.save(changed))
            self.assertTrue(plugin_map.validate_profile(self.profile, catalog)["errors"])

    def test_seed_and_compact_profile_keep_identity_and_mix_faders_free(self):
        self.dump["params"][7]["automatable"] = False
        plugin = plugin_params.catalog(self.save(self.dump))["plugins"][0]
        seed = plugin_seed.seed_profile(plugin, 10, 8)
        self.assertNotIn("Mix", [r["name"] for r in seed["controls"]])
        self.assertFalse(any(r["control"].startswith("fader") for r in seed["controls"]))
        core, _ = plugin_core.core_profile(seed)
        path = self.root / "core.toml"
        path.write_text(plugin_seed.render_toml(core), encoding="utf-8")
        self.assertEqual(plugin_map.load_profile(path)["sdk_identity"], plugin["sdk_identity"])

    def test_compare_exits_for_incompatible_changes_only(self):
        changed = copy.deepcopy(self.dump)
        changed["version"] += 1
        changed["params"][0]["display"] = "Off"
        changed["params"].append({**changed["params"][0], "index": 8, "name": "On"})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sdk_params.main([str(DUMP), str(self.save(changed))]), 0)
        changed["params"][1]["choices"].reverse()
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(sdk_params.main([str(DUMP), str(self.save(changed)), "--json"]), 2)
        report = json.loads(stdout.getvalue())
        self.assertTrue(report["review_required"])
        self.assertIn("choices", [r["field"] for r in report["changes"]])
        self.assertFalse(sdk_params.compare(self.dump, self.dump)["changes"])

    def test_malformed_inputs_give_actionable_context(self):
        for key, value in [("index", True), ("index", 7), ("index", 99), ("choices", [0]),
                           ("default", float("nan")), ("automatable", 1), ("label", None)]:
            with self.subTest(key=key, value=value):
                changed = copy.deepcopy(self.dump)
                changed["params"][0][key] = value
                with self.assertRaisesRegex(ValueError, "params.json"):
                    sdk_params.read_dump(self.save(changed))
