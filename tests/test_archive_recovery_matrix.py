import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/archive_recovery_matrix.py'
spec = importlib.util.spec_from_file_location('archive_recovery_matrix', SCRIPT)
matrix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matrix)


class RecoveryMatrixTests(unittest.TestCase):
    def test_all_fault_paths_have_quick_regression_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / 'report.json'
            self.assertEqual(matrix.run(report), 0)
            data = json.loads(report.read_text())
            self.assertTrue(data['complete'])
            self.assertEqual(data['failed'], 0)
            self.assertEqual(data['passed'], 7)
            self.assertEqual({row['fault'] for row in data['cases']}, set(matrix.FAULTS))
            with self.assertRaises(FileExistsError):
                matrix.run(report)

    def test_multiple_unicode_projects_and_empty_companions(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = matrix.exercise(Path(temporary), 0, 0, 2, 'unicode', 'healthy')
            self.assertEqual(result['payload_files'], 2)
