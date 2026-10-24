"""Bounded, read-only XPM container parsing for inspection and normalization."""

import gzip
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zlib


MAX_SOURCE_BYTES = 32 * 1024 * 1024
MAX_EXPANDED_BYTES = 64 * 1024 * 1024
MAX_XML_DEPTH = 128
MAX_XML_ELEMENTS = 200_000
MAX_JSON_DEPTH = 128
MAX_JSON_VALUES = 500_000


def read_payload(path: Path) -> tuple[bytes, bool]:
    if not path.is_file():
        raise ValueError(f'XPM input must be a regular file: {path}')
    with path.open('rb') as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError(f'XPM exceeds {MAX_SOURCE_BYTES} source bytes: {path}')
    compressed = raw.startswith(b'\x1f\x8b')
    if compressed:
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw = stream.read(MAX_EXPANDED_BYTES + 1)
        except (OSError, EOFError, zlib.error) as error:
            raise ValueError(f'invalid or truncated compressed XPM: {path}: {error}') from error
        if len(raw) > MAX_EXPANDED_BYTES:
            raise ValueError(f'XPM exceeds {MAX_EXPANDED_BYTES} expanded bytes: {path}')
    return raw, compressed


def parse_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'duplicate XPM JSON field: {key}')
            result[key] = value
        return result
    try:
        document = json.loads(raw, object_pairs_hook=unique)
    except RecursionError as error:
        raise ValueError('XPM JSON nesting is too deep to inspect safely') from error
    pending = [(document, 0)]
    values = 0
    while pending:
        value, depth = pending.pop()
        values += 1
        if depth > MAX_JSON_DEPTH or values > MAX_JSON_VALUES:
            raise ValueError('XPM JSON exceeds the nesting or value inspection limit')
        children = value.values() if isinstance(value, dict) else value if isinstance(value, list) else ()
        if len(children) + len(pending) + values > MAX_JSON_VALUES:
            raise ValueError('XPM JSON exceeds the value inspection limit')
        pending.extend((child, depth + 1) for child in children)
    return document


def serialized_document(raw: bytes):
    start = raw.find(b'{')
    if not raw.startswith(b'ACVS\n') or start < 0:
        raise ValueError('unsupported compressed MPC program header')
    header = raw[:start].decode('utf-8').rstrip('\n').splitlines()
    document = parse_json(raw[start:])
    if not isinstance(document, dict) or not isinstance(document.get('data', {}), dict):
        raise ValueError('compressed XPM document and data must be objects')
    data = document.get('data', {})
    if not isinstance(data.get('drum', {}), dict):
        raise ValueError('compressed XPM drum must be an object')
    instruments = data.get('drum', {}).get('instruments', [])
    if not isinstance(instruments, list):
        raise ValueError('compressed XPM instruments must be an array')
    if isinstance(data.get('type'), (dict, list)):
        raise ValueError('compressed XPM type must be a scalar')
    for instrument in instruments:
        if isinstance(instrument, dict) and not isinstance(instrument.get('layersv', []), list):
            raise ValueError('compressed XPM layersv must be an array')
    return header, document


class _BoundedTree(ET.TreeBuilder):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.elements = 0

    def start(self, tag, attrs):
        self.depth += 1
        self.elements += 1
        if self.depth > MAX_XML_DEPTH or self.elements > MAX_XML_ELEMENTS:
            raise ValueError('XPM XML exceeds the nesting or element inspection limit')
        return super().start(tag, attrs)

    def end(self, tag):
        result = super().end(tag)
        self.depth -= 1
        return result

    def doctype(self, name, pubid, system):
        raise ValueError('XPM XML document types/entities are not supported for inspection')


def xml_root(raw):
    return ET.fromstring(raw, parser=ET.XMLParser(target=_BoundedTree()))
