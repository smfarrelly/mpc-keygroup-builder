import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from mpc_keygroup_builder.roles import infer_role, load_role_overrides, role_matches


class RoleTests(unittest.TestCase):
    def test_infers_hierarchical_drum_and_fx_roles(self):
        self.assertEqual(infer_role("BD 808 Warm.wav"), "kick.primary")
        self.assertEqual(infer_role("CH 909 Sharp.wav"), "hihat.closed")
        self.assertEqual(infer_role("Ride Acoustic Full.wav"), "cymbal.ride")
        self.assertEqual(infer_role("Tom Acoustic Lo.wav"), "tom.low")
        self.assertEqual(infer_role("Shaker Tape.wav"), "percussion.shaker")
        self.assertEqual(infer_role("FX Club Chord.wav"), "fx.chord")
        self.assertEqual(infer_role("FX Vox Blip.wav"), "fx.vocal")

    def test_role_override_and_family_matching(self):
        self.assertEqual(
            infer_role("Odd.wav", {"odd.wav": "fx.transition"}),
            "fx.transition",
        )
        self.assertTrue(role_matches("percussion.shaker", "percussion"))
        self.assertTrue(role_matches("hihat.closed", "hihat.closed"))
        self.assertFalse(role_matches("hihat.closed", "hihat.open"))

    def test_load_role_overrides_normalizes_names(self):
        source = self.enterContext(TemporaryDirectory())
        path = Path(source) / "roles.toml"
        path.write_text('[roles]\n"Odd Hit.WAV" = "kick.primary"\n', encoding="utf-8")
        overrides = load_role_overrides(path)
        self.assertEqual(infer_role("folder/ODD HIT.wav", overrides), "kick.primary")

    def test_load_role_overrides_rejects_unknown_roles(self):
        source = self.enterContext(TemporaryDirectory())
        path = Path(source) / "roles.toml"
        path.write_text('[roles]\n"Odd Hit.wav" = "kick.secondary"\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unknown semantic role"):
            load_role_overrides(path)


if __name__ == "__main__":
    unittest.main()
