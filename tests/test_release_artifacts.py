import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


class ReleaseArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'scripts/check_release_artifacts.py'
        spec = importlib.util.spec_from_file_location('check_release_artifacts', path)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def wheel(self, root, extra=None, version='0.1.0'):
        path = root / 'package.whl'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('mpc_keygroup_builder-0.1.0.dist-info/METADATA', f'Name: mpc-keygroup-builder\nVersion: {version}\n')
            archive.writestr('mpc_keygroup_builder/__init__.py', '')
            archive.writestr('mpc_keygroup_builder-0.1.0.dist-info/licenses/LICENSE', 'MIT license fixture')
            if extra:
                archive.writestr(extra, '')
        return path

    def test_valid_metadata_and_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            report = self.module.inspect(self.wheel(Path(directory)), '0.1.0')
            self.assertEqual(report['members'], 3)
            self.assertEqual(len(report['sha256']), 64)

    def test_private_captured_and_unsafe_members_rejected(self):
        for name in ('work/secret.json', 'Samples/kick.WAV', 'capture.xpj', 'home.local.toml',
                     '../escape', '/absolute', 'x\\y', 'a/[ProjectData]/sample.bin', '.env', '.env.production', 'a//b'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):
                    self.module.inspect(self.wheel(Path(directory), name), '0.1.0')

    def test_mismatched_version_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                self.module.inspect(self.wheel(Path(directory), version='9.9.9'), '0.1.0')

    def test_case_collision_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.wheel(Path(directory), 'mpc_keygroup_builder/__INIT__.py')
            with self.assertRaisesRegex(ValueError, 'case-colliding'):
                self.module.inspect(path, '0.1.0')
