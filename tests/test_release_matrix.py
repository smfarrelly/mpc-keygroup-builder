import importlib.util
from pathlib import Path
import unittest


class ReleaseMatrixTests(unittest.TestCase):
    def test_matrix_has_unique_bounded_scenarios_and_all_families(self):
        path = Path(__file__).resolve().parents[1] / 'scripts/release_matrix.py'
        spec = importlib.util.spec_from_file_location('release_matrix', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cases = module.scenarios(True)
        self.assertEqual(len(cases), 810)
        self.assertEqual(len(set(cases)), 810)
        self.assertEqual(len(module.scenarios()), 6)
        self.assertEqual({case[0] for case in cases}, set(module.FAMILIES))
        self.assertTrue(all(20 <= case[4] <= 300 for case in cases))
