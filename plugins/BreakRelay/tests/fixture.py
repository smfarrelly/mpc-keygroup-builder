"""Create numbered stereo regions to verify role selection through the compiled VST."""

from pathlib import Path
import struct
import sys

folder = Path(sys.argv[1]) / "Content"
folder.mkdir(parents=True, exist_ok=True)
data = bytearray(b"BRK1")
for bank in range(2):
    data.extend(struct.pack("<IB", 32000, 8))
    for i, role in enumerate((0, 2, 1, 2, 0, 2, 1, 3)):
        value = 1000 * (1 + i + 8 * bank)
        data.extend(
            struct.pack("<BHHI", role, 8192 * i, min(65535, 8192 * (i + 1)), 1200)
        )
        data.extend(struct.pack("<hh", value, -value) * 1200)
(folder / "pair.brk").write_bytes(data)
