import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mpc_keygroup_builder import routing


class RoutingTests(unittest.TestCase):
    def test_invokes_detached_inspector_for_both_files_and_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination, inspector = root / "capture", root / "inspector"
            destination.mkdir()
            (inspector / "src").mkdir(parents=True)
            for name in routing.DEFAULT_PROJECTS:
                (destination / name).write_bytes(b"xpj")

            def fake_run(command, **kwargs):
                output = Path(command[command.index("--output") + 1])
                output.write_text(json.dumps({"command": command[3]}))

            with patch("mpc_keygroup_builder.routing.subprocess.run", side_effect=fake_run) as run:
                report = routing.inspect_capture(destination, inspector)
            self.assertEqual(run.call_count, 3)
            self.assertEqual(set(report), {"baseline", "changed", "comparison"})
            self.assertEqual(report["comparison"]["command"], "compare")


if __name__ == "__main__":
    unittest.main()
