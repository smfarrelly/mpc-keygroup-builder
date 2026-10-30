"""Read-only compatibility for WAVs with stale outer RIFF lengths."""

import struct
import hashlib
from pathlib import Path
import wave


def counted_zero_padding(channels: int, width: int, frames: int, extra: bytes) -> bool:
    """Recognize one RIFF alignment byte counted inside odd mono 24-bit data."""
    return channels == 1 and width == 3 and frames % 2 == 1 and extra == b'\0'


def inspect_pcm_file(path: Path) -> dict:
    """Read every declared PCM byte with bounded memory, without float decoding."""
    try:
        with path.open('rb') as source:
            view = complete_riff_view(source)
            adjusted = view is not source
            with wave.open(view, 'rb') as stream:
                channels, width, rate, frames, _, _ = stream.getparams()
                if channels not in (1, 2) or width not in (1, 2, 3, 4):
                    raise ValueError('PCM verification supports mono/stereo 8/16/24/32-bit WAVs')
                if rate <= 0 or frames <= 0:
                    raise ValueError('empty WAV or invalid sample rate')
                expected = frames * channels * width
                digest = hashlib.sha256()
                size = 0
                padding_ignored = False
                while chunk := stream.readframes(8192):
                    remaining = expected - size
                    if len(chunk) > remaining:
                        if counted_zero_padding(channels, width, frames, chunk[remaining:]) and not padding_ignored:
                            chunk = chunk[:remaining]
                            padding_ignored = True
                        else:
                            raise ValueError('WAV data contains an incomplete PCM frame')
                    size += len(chunk)
                    digest.update(chunk)
                if size != expected:
                    raise ValueError(f'truncated WAV: expected {expected} PCM bytes, got {size}')
    except (wave.Error, EOFError) as error:
        raise ValueError(f'unreadable WAV: {error or "truncated header"}') from error
    return {'status': 'pass', 'channels': channels, 'sample_width_bytes': width,
            'sample_rate': rate, 'frames': frames, 'pcm_bytes': size,
            'pcm_sha256': digest.hexdigest(), 'riff_length_adjusted': adjusted,
            'data_padding_ignored': padding_ignored}


class _RiffLengthView:
    def __init__(self, source, base, size):
        self.source = source
        self.offset = base + 4
        self.length = struct.pack('<I', size)

    def read(self, size=-1):
        start = self.source.tell()
        data = self.source.read(size)
        first = max(start, self.offset)
        last = min(start + len(data), self.offset + 4)
        if first < last:
            data = data[:first-start] + self.length[first-self.offset:last-self.offset] + data[last-start:]
        return data

    def tell(self):
        return self.source.tell()

    def seek(self, *args):
        return self.source.seek(*args)


def complete_riff_view(source):
    """Patch only the virtual RIFF length after validating every physical chunk.

    Some MPC vendor presets inserted metadata without increasing the outer
    RIFF length. Data chunk sizes are correct and all bytes remain present.
    Never extend a chunk, invent audio, alter the source, or accept arbitrary
    trailing bytes as audio. Inspection seeks over payloads without copying.
    """
    base = source.tell()
    try:
        header = source.read(12)
        if len(header) != 12 or header[:4] != b'RIFF' or header[8:] != b'WAVE':
            return source
        declared = struct.unpack_from('<I', header, 4)[0]
        source.seek(0, 2)
        end = source.tell()
        actual = end - base - 8
        if not declared < actual <= 0xFFFFFFFF:
            return source
        offset = base + 12
        seen = set()
        for _ in range(10_000):
            if offset == end:
                if {b'fmt ', b'data'} <= seen:
                    return _RiffLengthView(source, base, actual)
                return source
            if offset + 8 > end:
                return source
            source.seek(offset)
            tag, size = struct.unpack('<4sI', source.read(8))
            if offset + 8 + size > end:
                return source
            if tag in {b'fmt ', b'data'} and tag in seen:
                return source
            seen.add(tag)
            chunk_end = offset + 8 + size
            # PCM writers commonly omit the pad byte on a final odd-sized chunk.
            offset = chunk_end if chunk_end == end else chunk_end + size % 2
        return source
    finally:
        source.seek(base)
