import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder.device import load_device


class DeviceProfileTests(unittest.TestCase):
    def test_key37_profile_has_eight_16_pad_banks(self):
        root = Path(__file__).parents[1]
        device = load_device(root / "devices/mpc-key-37.toml")
        self.assertEqual(device.keys, 37)
        self.assertEqual(device.pads_per_bank, 16)
        self.assertEqual(device.capacity, 128)
        self.assertEqual(device.label(1), "A01")
        self.assertEqual(device.label(16), "A16")
        self.assertEqual(device.label(17), "B01")
        self.assertEqual(device.label(128), "H16")

    def test_key61_profile_has_sixty_one_keys_and_full_pad_capacity(self):
        root = Path(__file__).parents[1]
        device = load_device(root / "devices/mpc-key-61.toml")
        self.assertEqual(device.keys, 61)
        self.assertEqual(device.pads_per_bank, 16)
        self.assertEqual(device.capacity, 128)

    def test_rejects_capacity_above_128(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.toml"
            path.write_text(
                'schema_version=1\nid="bad"\nname="Bad"\nkeys=0\n'
                'pad_rows=5\npad_columns=5\nbanks=["A","B","C","D","E","F"]\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "128"):
                load_device(path)


if __name__ == "__main__":
    unittest.main()
