import struct
import tempfile
import unittest
import wave
from pathlib import Path

from mpc_keygroup_builder import break_relay, body_print


class BankTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.wav = self.root / "loop.wav"
        with wave.open(str(self.wav), "wb") as w:
            w.setparams((1, 2, 8000, 0, "NONE", ""))
            w.writeframes(struct.pack("<hhhh", 8000, -8000, 2000, 1000) * 4000)
        self.spec = """[[breaks]]
file="loop.wav"
beats=4
bpm=120
slices=[["kick",0,1],["snare",1,2],["hat",2,3],["pickup",3,4]]
"""
        self.manifest = self.root / "pair.toml"
        self.manifest.write_text(self.spec * 2)

    def test_pack_preserves_pcm_and_positions_with_canonical_stereo_frames(self):
        dest = self.root / "Content"
        break_relay.build(self.manifest, self.root, dest)
        data = (dest / "pair.brk").read_bytes()
        self.assertEqual(data[:4], b"BRK1")
        self.assertEqual(struct.unpack_from("<IB", data, 4), (8000, 4))
        self.assertEqual(struct.unpack_from("<BHHI", data, 9), (0, 0, 16384, 4000))
        self.assertEqual(
            struct.unpack_from("<hhhh", data, 18), (8000, 8000, -8000, -8000)
        )
        with self.assertRaisesRegex(ValueError, "new Content"):
            break_relay.build(self.manifest, self.root, dest)

    def test_invalid_roles_and_bounds_publish_nothing(self):
        for old, new in [("pickup", "hat"), ("3,4", "3,5"), ("0,1", "0,0")]:
            self.manifest.write_text(self.spec + self.spec.replace(old, new))
            with self.assertRaises(ValueError):
                break_relay.build(self.manifest, self.root, self.root / "Content")
            self.assertFalse((self.root / "Content").exists())

    def test_body_pair_normalized_and_bounded(self):
        k = body_print.reflections(self.wav)
        self.assertLessEqual(len(k), 48)
        self.assertAlmostEqual(sum(v * v for v in k.values()), 1)
        dest = self.root / "Bodies"
        body_print.build([self.wav, self.wav], dest)
        self.assertEqual(
            (dest / "bodies.bin").read_bytes()[:5], b"BOD1" + bytes([len(k)])
        )
        with self.assertRaisesRegex(ValueError, "new Content"):
            body_print.build([self.wav, self.wav], dest)
