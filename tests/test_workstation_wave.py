import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import creative_review
from mpc_keygroup_builder.workstation_wave import build_wave


class WorkstationWaveTests(unittest.TestCase):
    def setUp(self):
        self.repository = Path(__file__).resolve().parents[1]

    def test_builds_deterministic_ranked_portable_wave_and_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "one/wave"
            second = root / "two/wave"
            report = build_wave(
                self.repository / "recipes", first,
                families=("dusty", "house"), seeds_per_family=2, seed_start=10,
            )
            build_wave(
                self.repository / "recipes", second,
                families=("dusty", "house"), seeds_per_family=2, seed_start=10,
            )
            self.assertEqual(report["software_status"], "pass")
            self.assertEqual(report["hardware_status"], "deferred")
            self.assertEqual(report["summary"]["candidates"], 4)
            self.assertEqual(report["recipe_audit"]["status"], "pass")
            self.assertEqual(
                len({item["structural_fingerprint"] for item in report["candidates"]}), 4
            )
            scores = [item["score"]["exploration_score"] for item in report["candidates"]]
            self.assertEqual(scores, sorted(scores, reverse=True))
            self.assertEqual(
                [item["rank"] for item in report["candidates"]], [1, 2, 3, 4]
            )
            self.assertEqual(
                (first / "checksums.json").read_bytes(),
                (second / "checksums.json").read_bytes(),
            )
            self.assertTrue((first / "Instrument/FG Portable Cross Kit.xpm").is_file())
            for item in report["candidates"]:
                candidate = first / item["paths"]["root"]
                self.assertTrue((candidate / "idea.mid").is_file())
                self.assertEqual(
                    sorted(path.stem for path in (candidate / "Sequences").glob("*.mid")),
                    ["breakdown", "build", "main", "main-b", "outro"],
                )
                self.assertEqual(
                    set(item["score"]["components"]),
                    {
                        "event_density", "syncopation", "melody_range",
                        "melody_variation", "harmonic_movement",
                        "arrangement_contrast", "drum_role_coverage",
                    },
                )
            html = (first / "review.html").read_text(encoding="utf-8")
            self.assertIn("localStorage", html)
            self.assertIn("Export JSON", html)
            self.assertIn("Compare candidates", html)
            self.assertIn("Semantic drum grid", html)
            self.assertNotIn(str(root), html)
            self.assertNotIn("https://", html)
            manifest = (first / "COPY_MANIFEST.txt").read_text(encoding="utf-8")
            self.assertIn("COPY_MANIFEST.txt", manifest)
            self.assertIn("checksums.json", manifest)
            checksums = json.loads((first / "checksums.json").read_text())
            for relative, expected in checksums.items():
                self.assertEqual(
                    hashlib.sha256((first / relative).read_bytes()).hexdigest(), expected
                )

    def test_review_renderer_validates_input_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wave = root / "wave"
            report = build_wave(
                self.repository / "recipes", wave,
                families=("ambient",), seeds_per_family=1,
            )
            data = creative_review.review_data(report)
            self.assertEqual(data["kind"], "mpc-creative-wave-review")
            self.assertEqual(len(data["fingerprint"]), 16)
            output = root / "standalone-review.html"
            self.assertEqual(
                creative_review.build_review(wave / "wave.json", output), output.resolve()
            )
            with self.assertRaises(FileExistsError):
                creative_review.build_review(wave / "wave.json", output)

            external = root / "external.html"
            external.write_text("preserve")
            symlink = root / "review-link.html"
            symlink.symlink_to(external)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                creative_review.build_review(
                    wave / "wave.json", symlink, force=True
                )
            self.assertEqual(external.read_text(), "preserve")
            with self.assertRaisesRegex(ValueError, "mpc-workstation-wave"):
                creative_review.review_data({"kind": "wrong", "candidates": []})

    def test_invalid_scope_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "unknown recipe family"):
                build_wave(
                    self.repository / "recipes", root / "unknown",
                    families=("not-a-family",), seeds_per_family=1,
                )
            with self.assertRaisesRegex(ValueError, "1..32"):
                build_wave(self.repository / "recipes", root / "too-many", seeds_per_family=33)
            empty = root / "empty"
            empty.mkdir()
            with self.assertRaisesRegex(ValueError, "recipe audit failed"):
                build_wave(empty, root / "invalid", families=("dusty",), seeds_per_family=1)
            with self.assertRaises(FileNotFoundError):
                build_wave(
                    self.repository / "recipes", root / "missing-program",
                    families=("dusty",), seeds_per_family=1,
                    program_path=root / "absent.xpm",
                )
            self.assertFalse((root / "unknown").exists())
            self.assertFalse((root / "too-many").exists())
            self.assertFalse((root / "invalid").exists())
            self.assertFalse((root / "missing-program").exists())
            self.assertFalse(list(root.glob(".missing-program.staging-*")))


if __name__ == "__main__":
    unittest.main()
