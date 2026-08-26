import csv
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import library


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


if __name__ == "__main__":
    unittest.main()
