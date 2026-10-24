import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest

from mpc_keygroup_builder.home import load_config
from mpc_keygroup_builder.entrypoints import invoke


class HomeConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'home.local.toml'

    def test_relative_paths_follow_config_not_current_directory(self):
        self.config.write_text('format=1\nledger="ledger.csv"\nbundles=["wave"]\n')
        result = load_config(self.config)
        self.assertEqual(result['ledger'], self.root / 'ledger.csv')
        self.assertEqual(result['bundles'], [self.root / 'wave'])

    def test_minimal_config_and_public_command(self):
        self.config.write_text('format=1\n')
        output = self.root / 'home.html'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(invoke('mpc-tools', ['home', '--config', str(self.config), '--output', str(output)]), 0)
        self.assertIn('No ledger selected', output.read_text())

    def test_invalid_format_unknown_fields_and_wrong_types(self):
        for text in ('', 'format=true', 'format=2', 'format=1\ncommand="erase"',
                     'format=1\nledger=[]', 'format=1\nledger=" "',
                     'format=1\nbundles="wave"', 'format=1\nbundles=[4]'):
            with self.subTest(text=text):
                self.config.write_text(text)
                with self.assertRaises(ValueError):
                    load_config(self.config)

    def test_symbolic_link_config_rejected(self):
        self.config.write_text('format=1\n')
        alias = self.root / 'alias.toml'
        alias.symlink_to(self.config)
        with self.assertRaises(ValueError):
            load_config(alias)

    def test_ambiguous_cli_config_overrides_rejected(self):
        self.config.write_text('format=1\n')
        output = self.root / 'home.html'
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            invoke('mpc-tools', ['home', '--config', str(self.config), '--ledger', 'other.csv', '--output', str(output)])
        self.assertEqual(raised.exception.code, 2)
        self.assertFalse(output.exists())

    def test_explicit_output_is_still_required(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            invoke('mpc-tools', ['home', '--config', str(self.config)])
        self.assertEqual(raised.exception.code, 2)
