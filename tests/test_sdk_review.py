import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from mpc_keygroup_builder import bundle_verify, sdk_review

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "tests/fixtures/sdk/stereo-delay.json"
PROFILE = ROOT / "midi/sdk-examples/stereo-delay.toml"


class SoftwareReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.native = self.root / "native.so"
        self.host = self.root / "host_sim"
        self.native.write_bytes(b"fake native Input")
        self.host.write_bytes(b"fake host")
        self.out = self.root / "review"
        self.kwargs = dict(host=self.host, native=self.native, output=self.out)
        self.dump = subprocess.CompletedProcess([], 0, EXAMPLE.read_text(), "")
        self.passed = subprocess.CompletedProcess([], 0, "Result: PASS  (20 passed, 0 warnings, 0 failures)\n", "")

    def test_complete_review_publishes_all_files_and_refuses_replacement(self):
        with patch.object(sdk_review, "run_host", side_effect=[self.dump, self.passed]) as run:
            report = sdk_review.review(**self.kwargs, baseline=EXAMPLE, profile=PROFILE, notes="36,40")
            self.assertEqual(run.call_args.args[2], ["test", "--playing", "--notes", "36,40"])
        self.assertEqual(report["software_status"], "pass")
        self.assertEqual(report["hardware_status"], "untested")
        self.assertEqual(report["parameter_comparison"]["changes"], [])
        for path in ["params.json", "host-sim.log", "worksheets/mpc-midi-learn-all.csv", "companion.html"]:
            self.assertTrue((self.out / path).is_file(), path)
        self.assertGreater(bundle_verify.verify_bundle(self.out)["verified_files"], 4)
        (self.out / "host-sim.log").write_text("different evidence")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            bundle_verify.verify_bundle(self.out)
        with self.assertRaises(FileExistsError):
            sdk_review.review(**self.kwargs)

    def test_missing_summary_or_nonzero_exit_never_passes(self):
        for stdout, code in [("No summary", 0), (self.passed.stdout, 1),
                             (self.passed.stdout + "Result: FAIL (interrupted)", 0),
                             ("Result: PASS  (0 passed, 0 warnings, 0 failures)", 0)]:
            with self.subTest(stdout=stdout, code=code):
                run = subprocess.CompletedProcess([], code, stdout, "")
                self.assertEqual(sdk_review.simulator_result(run)["status"], "fail")

    def test_warn_writes_report_but_does_not_pass_cli(self):
        warn = subprocess.CompletedProcess([], 0, "Result: PASS with warnings  (18 passed, 1 warnings, 0 failures)", "")
        with patch.object(sdk_review, "run_host", side_effect=[self.dump, warn]), contextlib.redirect_stdout(io.StringIO()):
            rc = sdk_review.main([str(self.native), "--host-sim", str(self.host), "--output", str(self.out)])
        self.assertEqual(rc, 2)
        self.assertEqual(json.loads((self.out / "review.json").read_text())["software_status"], "warn")

    def test_drift_and_wrong_package_retained_as_review_evidence(self):
        data = json.loads(self.dump.stdout)
        data["params"][3]["choices"] = ["different"]
        baseline = self.root / "prior.json"
        baseline.write_text(json.dumps(data))
        with patch.object(sdk_review, "run_host", side_effect=[self.dump, self.passed]):
            report = sdk_review.review(**self.kwargs, baseline=baseline, package=self.root / "missing")
        self.assertEqual(report["software_status"], "fail")
        self.assertEqual(len(report["findings"]), 2)
        self.assertTrue((self.out / "host-sim.log").is_file())

    def test_timeout_or_concurrent_input_change_leaves_no_partial_directory(self):
        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("host_sim", 1)):
            with self.assertRaisesRegex(ValueError, "timed out"):
                sdk_review.review(**self.kwargs, timeout=1)
        def changed(host, native, args, timeout):
            if args == ["dump"]:
                return self.dump
            native.write_bytes(b"new build")
            return self.passed
        with patch.object(sdk_review, "run_host", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "changed during"):
                sdk_review.review(**self.kwargs)
        self.assertFalse(self.out.exists())
        self.assertFalse(list(self.root.glob(".review.review-*")))

    def test_invalid_notes_rejected_before_launch(self):
        with patch.object(sdk_review, "run_host") as run:
            with self.assertRaisesRegex(ValueError, "notes"):
                sdk_review.review(**self.kwargs, notes="128")
            run.assert_not_called()
