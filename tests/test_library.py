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

    def test_rejects_unknown_enumerated_filters(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "status.csv"
            path.write_text(
                "path,program_type,hardware_status,favorite,scratchpad_role,notes\n"
                "Kit.xpm,Drum,pass,yes,drums,good\n"
            )
            with self.assertRaisesRegex(ValueError, "invalid hardware status"):
                library.query(path, hardware="psas")
            with self.assertRaisesRegex(ValueError, "invalid favorite status"):
                library.query(path, favorite="yse")
            self.assertEqual(len(library.query(path, hardware="PASS", favorite="YES")), 1)

    def test_output_cannot_replace_the_input_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "status.csv"
            original = "path,program_type,hardware_status,favorite,scratchpad_role,notes\n"
            ledger.write_text(original)
            with self.assertRaisesRegex(ValueError, "replace the input ledger"):
                library.write_output(ledger, ledger, "destroyed\n")
            self.assertEqual(ledger.read_text(), original)

    def test_output_rejects_symlinks_and_publishes_into_new_parents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "status.csv"
            ledger.write_text("ledger\n")
            outside = root / "outside.txt"
            outside.write_text("keep\n")
            link = root / "report.txt"
            link.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                library.write_output(link, ledger, "replace\n")
            self.assertEqual(outside.read_text(), "keep\n")

            output = root / "new" / "reports" / "query.json"
            self.assertEqual(library.write_output(output, ledger, "[]\n"), output.resolve())
            self.assertEqual(output.read_text(), "[]\n")


if __name__ == "__main__":
    unittest.main()
