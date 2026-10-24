import contextlib
import io
import json
import shlex
import unittest
from pathlib import Path
from unittest.mock import patch

from mpc_keygroup_builder.entrypoints import COMMANDS, invoke
from mpc_keygroup_builder.start import WORKFLOWS


class StartTests(unittest.TestCase):
    def test_guidance_needs_no_storage_access(self):
        with patch('mpc_keygroup_builder.ux.version', return_value='test'), patch.object(Path, 'is_dir', side_effect=AssertionError('storage discovery')), patch.object(Path, 'read_text', side_effect=AssertionError('file read')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(invoke('mpc-tools', ['start', '--json']), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(set(report['workflows']), set(WORKFLOWS))
        self.assertIn('no commands executed', report['boundary'])

    def test_each_goal_has_valid_command_and_documentation(self):
        root = Path(__file__).resolve().parents[1]
        for goal, item in WORKFLOWS.items():
            self.assertIn(shlex.split(item['command'])[0], COMMANDS)
            self.assertTrue((root / item['guide']).is_file())
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(invoke('mpc-tools', ['start', goal, '--json']), 0)
            self.assertEqual(list(json.loads(output.getvalue())['workflows']), [goal])

    def test_unknown_goal_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            invoke('mpc-tools', ['start', 'erase'])
        self.assertEqual(raised.exception.code, 2)
