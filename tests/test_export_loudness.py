import json
import math
from pathlib import Path
import shutil
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import wave

from mpc_keygroup_builder import export_loudness as meter


@unittest.skipUnless(shutil.which("ffmpeg"), "requires FFmpeg for end-to-end WAV measurement")
class ExportLoudnessTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)

    def wav(self, name, signal, frames=96000, channels=2):
        path = self.folder / (name + ".wav")
        with wave.open(str(path), "wb") as f:
            f.setparams((channels, 2, 48000, 0, "NONE", ""))
            f.writeframes(b"".join(struct.pack("<h", round(signal(i)*32767))*channels
                                   for i in range(frames)))
        return path

    def test_calibration_reference_and_mono_playback(self):
        def tone(i):
            return .1*math.sin(2*math.pi*1000*i/48000)
        source = self.wav("MPC export", tone, channels=1)
        ref = self.wav("L6 reference", lambda i: 2*tone(i))
        result = meter.check(source, ref)
        self.assertAlmostEqual(result["export"]["integrated_lufs"], -20, delta=.2)
        self.assertAlmostEqual(result["export"]["true_peak_dbtp"], -20, delta=.05)
        self.assertAlmostEqual(result["gain_to_reference_db"], 6.02, delta=.05)
        self.assertTrue(result["reference_reachable_with_gain"])
        self.assertIn("clean gain", meter.report(result))
        limited = meter.check(source, ref, -18)
        self.assertFalse(limited["reference_reachable_with_gain"])
        self.assertIn("exceed", meter.report(limited))
        hot = meter.check(source, ceiling=-22)
        self.assertIn("Lower gain", meter.report(hot))

    def test_intersample_peak_in_partial_final_window(self):
        # Fs/4 with 45-degree phase: reconstructed peaks exceed the PCM peaks by ~3 dB.
        def final_burst(i):
            if i < 48000:
                return 0
            return .8*math.sin(math.pi*i/2 + math.pi/4)*min(1,(i-48000)/100,(49200-i)/100)
        path = self.wav("late peak", final_burst, frames=49200)
        result = meter.measure(path)
        self.assertAlmostEqual(result["true_peak_dbtp"], 20*math.log10(.8), delta=.1)
        self.assertEqual(result["peak_window_start_seconds"], 1)

    def test_short_clip_and_silence(self):
        silent = self.wav("silence", lambda i: 0)
        short = self.wav("short", lambda i: .3, frames=2400)
        result = meter.check(silent, short)
        self.assertIsNone(result["export"]["true_peak_dbtp"])
        self.assertIsNone(result["reference"]["integrated_lufs"])
        self.assertIsNotNone(result["reference"]["true_peak_dbtp"])
        self.assertIsNone(result["reference_reachable_with_gain"])
        json.dumps(result, allow_nan=False)
        self.assertIn("routing", meter.report(result))

    def test_broken_wav_and_dependencies(self):
        path = self.folder / "broken.wav"
        path.write_bytes(b"bad recording")
        with self.assertRaisesRegex(ValueError, "Could not measure"):
            meter.check(path)
        with patch.object(shutil, "which", return_value=None):
            with self.assertRaisesRegex(ValueError, "Install FFmpeg"):
                meter.check(path)
        with self.assertRaisesRegex(ValueError, "ceiling"):
            meter.check(path, ceiling=float("nan"))
