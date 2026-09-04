import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import schema


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_every_schema_resource_is_json_schema_with_existing_examples(self):
        self.assertEqual(len(schema.SCHEMAS), 9)
        for name, spec in schema.SCHEMAS.items():
            with self.subTest(schema=name):
                document = schema.schema_document(name)
                self.assertEqual(document["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertEqual(document["type"], "object")
                self.assertTrue(document["title"])
                self.assertTrue(spec.examples)
                for example in spec.examples:
                    self.assertTrue((self.root / example).is_file(), example)

    def test_all_published_examples_pass_native_semantic_validation(self):
        for name, spec in schema.SCHEMAS.items():
            paths = [self.root / example for example in spec.examples]
            with self.subTest(schema=name):
                results = schema.validate_files(name, paths)
                self.assertTrue(results)
                self.assertEqual({row["status"] for row in results}, {"pass"}, results)

    def test_validation_reports_all_files_without_stopping_at_first_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid = root / "invalid.toml"
            invalid.write_text('schema_version = 1\nname = "Missing geometry"\n', encoding="utf-8")
            results = schema.validate_files(
                "device-profile", [invalid, self.root / "devices/mpc-key-37.toml"]
            )
            self.assertEqual([row["status"] for row in results], ["fail", "pass"])
            self.assertIn("banks", results[0]["error"])

    def test_cli_can_list_show_and_validate(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(schema.main(["list", "--json"]), 0)
        self.assertEqual(len(json.loads(output.getvalue())["schemas"]), 9)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(schema.main(["show", "plugin-profile"]), 0)
        self.assertEqual(json.loads(output.getvalue())["title"], "Launch Control plugin performance profile")

        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                schema.main(
                    [
                        "validate",
                        "layout-preset",
                        str(self.root / "layouts/right-handed-performance.toml"),
                    ]
                ),
                0,
            )


if __name__ == "__main__":
    unittest.main()
