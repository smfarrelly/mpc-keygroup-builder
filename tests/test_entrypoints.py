import contextlib
import io
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from mpc_keygroup_builder import entrypoints, ux


class EntrypointTests(unittest.TestCase):
    def test_windows_console_launcher_suffix_is_supported(self):
        previous = sys.argv
        output = io.StringIO()
        try:
            sys.argv = [r"C:\\Tools\\mpc-tools.exe", "--version"]
            with contextlib.redirect_stdout(output):
                status = entrypoints.main()
        finally:
            sys.argv = previous
        self.assertEqual(status, 0)
        self.assertIn("mpc-tools 0.1.0", output.getvalue())

    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_every_published_script_has_dispatch_metadata(self):
        project = tomllib.loads((self.root / "pyproject.toml").read_text())
        scripts = project["project"]["scripts"]
        self.assertEqual(set(scripts), set(entrypoints.COMMANDS))
        self.assertEqual(set(scripts.values()), {"mpc_keygroup_builder.entrypoints:main"})
        for spec in entrypoints.COMMANDS.values():
            self.assertTrue(spec.summary)
            self.assertTrue((self.root / spec.documentation).is_file())

    def test_every_published_command_has_functional_short_and_long_help(self):
        for command in entrypoints.COMMANDS:
            for flag in ("-h", "--help"):
                with self.subTest(command=command, flag=flag):
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit) as raised:
                            entrypoints.invoke(command, [flag])
                    self.assertEqual(raised.exception.code, 0)

    def test_expected_failure_is_contextual_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.xpm"
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                status = entrypoints.invoke(
                    "mpc-program-designer",
                    [str(missing), "--output", str(Path(directory) / "viewer.html")],
                )
            self.assertEqual(status, 2)
            rendered = error.getvalue()
            self.assertIn("ERROR:", rendered)
            self.assertIn("NEXT:", rendered)
            self.assertIn("MPC_DEBUG=1", rendered)
            self.assertNotIn("Traceback", rendered)

    def test_front_door_lists_categories_and_reports_doctor(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(ux._commands("Creative MIDI", False), 0)
        self.assertIn("mpc-workstation-idea", output.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ux._doctor(False), 0)

    def test_resume_reports_exact_paths_and_next_action(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sd = root / "CARD"
            (sd / "Projects" / "Volca").mkdir(parents=True)
            (sd / "Projects" / "Boot.xpj").write_bytes(b"baseline")
            checkpoint = root / "checkpoint.toml"
            checkpoint.write_text(
                'title = "Test rig"\nbaseline_relative = "Projects/Boot.xpj"\n'
                'working_relative = "Projects/Volca/Base.xpj"\ntarget_relative = "Projects/Done.xpj"\n'
                'next_action = "Create the target."\n[[routes]]\ntrack = 1\nname = "KEYS"\nchannel = 1\n'
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(ux._resume(checkpoint, sd, False), 0)
            rendered = output.getvalue()
            self.assertIn("Baseline FOUND", rendered)
            self.assertIn(str(sd / "Projects" / "Done.xpj"), rendered)
            self.assertIn("NEXT: Create the target.", rendered)


if __name__ == "__main__":
    unittest.main()
