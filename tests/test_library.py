import csv
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import entrypoints, library


class LibraryTests(unittest.TestCase):
    def test_combines_exact_filters_and_text_search(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "status.csv"
            fields = ["path", "program_type", "hardware_status", "favorite", "scratchpad_role", "notes"]
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"path": "Warm Bass.xpm", "program_type": "Keygroup", "hardware_status": "pass", "favorite": "yes", "scratchpad_role": "bass", "notes": "round"})
                writer.writerow({"path": "Kit.xpm", "program_type": "Drum", "hardware_status": "pass", "favorite": "no", "scratchpad_role": "drums", "notes": "punchy"})
            rows = library.query(path, program_type="keygroup", favorite="yes", search="round")
            self.assertEqual([row["path"] for row in rows], ["Warm Bass.xpm"])
            self.assertIn("Warm Bass.xpm", library.render(rows, "text"))

    def test_rejects_missing_headers_and_malformed_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "status.csv"
            cases = (
                ("path,program_type\nKit.xpm,Drum\n", "missing fields"),
                (
                    "path,program_type,hardware_status,favorite,scratchpad_role,notes\n"
                    "Kit.xpm,Drum,pass,no,drums,good,unexpected\n",
                    "row 2 has the wrong number of columns",
                ),
            )
            for contents, message in cases:
                with self.subTest(message=message):
                    path.write_text(contents)
                    with self.assertRaisesRegex(ValueError, message):
                        library.query(path)

    def test_malformed_ledger_is_friendly_through_installed_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "status.csv"
            path.write_text("path,program_type\nKit.xpm,Drum\n")
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                status = entrypoints.invoke("mpc-library", [str(path)])
            self.assertEqual(status, 2)
            self.assertIn("program ledger is missing fields", error.getvalue())
            self.assertNotIn("Traceback", error.getvalue())


if __name__ == "__main__":
    unittest.main()
