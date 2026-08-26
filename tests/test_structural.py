import unittest

from mpc_keygroup_builder import structural


class StructuralTests(unittest.TestCase):
    def test_reports_stable_json_pointer_changes(self):
        before = {"a/b": [1, {"x": True}], "removed": 1}
        after = {"a/b": [2, {"x": "yes"}, 3], "added": 4}
        changes = structural.compare(before, after)
        self.assertEqual(
            [(item["path"], item["kind"]) for item in changes],
            [
                ("/a~1b/0", "changed"),
                ("/a~1b/1/x", "type"),
                ("/a~1b/2", "added"),
                ("/added", "added"),
                ("/removed", "removed"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
