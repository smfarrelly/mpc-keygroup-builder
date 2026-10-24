import ctypes
import errno
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from mpc_keygroup_builder import publication


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / '.stage'
        self.stage.mkdir()
        (self.stage / 'keep').write_text('verified payload')
        self.output = self.root / 'published'

    @unittest.skipUnless(sys.platform.startswith('linux') or sys.platform in ('darwin', 'win32'), 'requires native exclusive rename')
    def test_publish_moves_complete_directory(self):
        publication.publish_directory(self.stage, self.output)
        self.assertFalse(self.stage.exists())
        self.assertEqual((self.output / 'keep').read_text(), 'verified payload')

    def test_existing_empty_directory_is_not_replaced(self):
        self.output.mkdir()
        inode = self.output.stat().st_ino
        with self.assertRaises(FileExistsError):
            publication.publish_directory(self.stage, self.output)
        self.assertEqual(self.output.stat().st_ino, inode)
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertTrue((self.stage / 'keep').is_file())

    def test_existing_file_nonempty_directory_and_dangling_link_survive(self):
        for kind in ('file', 'directory', 'link'):
            with self.subTest(kind=kind):
                output = self.root / kind
                if kind == 'file':
                    output.write_text('keep')
                elif kind == 'directory':
                    output.mkdir()
                    (output / 'keep').write_text('keep')
                else:
                    output.symlink_to(self.root / 'missing', target_is_directory=True)
                with self.assertRaises(OSError):
                    publication.publish_directory(self.stage, output)
                self.assertTrue(output.exists() or output.is_symlink())
                self.assertTrue(self.stage.is_dir())

    def test_invalid_stage_and_different_parent_refused(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.stage, target_is_directory=True)
        with self.assertRaises(ValueError):
            publication.publish_directory(alias, self.output)
        with self.assertRaises(ValueError):
            publication.publish_directory(self.stage, self.root / 'nested/output')
        with self.assertRaises(ValueError):
            publication.publish_directory(self.stage, self.stage)

    def test_unsupported_platform_fails_closed_without_rename(self):
        with patch.object(publication.sys, 'platform', 'unknown'), patch.object(publication.os, 'rename') as rename:
            with self.assertRaisesRegex(OSError, 'unavailable'):
                publication.publish_directory(self.stage, self.output)
            rename.assert_not_called()
        self.assertTrue(self.stage.exists())
        self.assertFalse(self.output.exists())

    def test_unsupported_filesystem_does_not_fall_back_to_overwriting_rename(self):
        function = Mock(return_value=-1)
        library = Mock(renameat2=function)
        with patch.object(publication.sys, 'platform', 'linux'), patch.object(publication.ctypes, 'CDLL', return_value=library), patch.object(publication.ctypes, 'get_errno', return_value=errno.ENOTSUP), patch.object(publication.os, 'rename') as rename:
            with self.assertRaisesRegex(OSError, 'does not support'):
                publication.publish_directory(self.stage, self.output)
            rename.assert_not_called()
        self.assertEqual(function.call_args.args[-1], 1)

    def test_darwin_adapter_uses_exclusive_flag(self):
        function = Mock(return_value=0)
        with patch.object(publication.sys, 'platform', 'darwin'), patch.object(publication.ctypes, 'CDLL', return_value=Mock(renamex_np=function)):
            publication.publish_directory(self.stage, self.output)
        self.assertEqual(function.call_args.args[-1], 0x4)
        self.assertEqual(function.argtypes, (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint))

    def test_windows_adapter_uses_documented_nonoverwriting_rename(self):
        with patch.object(publication.sys, 'platform', 'win32'), patch.object(publication.os, 'rename') as rename:
            publication.publish_directory(self.stage, self.output)
        rename.assert_called_once_with(self.stage, self.output)
