import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_sd_programs.py"
SPEC = importlib.util.spec_from_file_location("audit_sd_programs", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AuditTests(unittest.TestCase):
    def test_xml_sample_name_resolves_wav_by_stem(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            program = root / "Kit.xpm"
            program.write_text(
                '<MPCVObject><Program type="Drum"><Instruments><Layer>'
                '<SampleName>Kick One</SampleName><SampleFile></SampleFile>'
                '</Layer></Instruments></Program></MPCVObject>',
                encoding="utf-8",
            )
            (root / "Kick One.WAV").write_bytes(b"audio")
            result = MODULE.audit_program(program, root)
            self.assertEqual(result.status, "pass")
            self.assertEqual(result.resolved, 1)

    def test_missing_program_data_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = MODULE.resolve_references(["missing.wav"], root / "absent", recursive=False)
            self.assertEqual(result[1], ["missing.wav"])


if __name__ == "__main__":
    unittest.main()
