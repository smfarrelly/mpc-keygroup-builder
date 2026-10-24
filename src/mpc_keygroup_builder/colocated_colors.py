"""Preservation-first XML Drum coloring without sample relocation."""

from __future__ import annotations

import os
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from .programs import colorize_drum_program, detect_program_type

# Do not match ProgramPads-v2.10 or other versioned metadata blocks.
PAD_BLOCK = re.compile(rb'<ProgramPads(?:\s[^>]*)?>.*?</ProgramPads>', re.DOTALL)


def colorize_colocated(
    source: Path, destination: Path, palette: dict[str, int], *,
    overrides: dict[str, str] | None = None,
    color_template: Path | None = None, dry_run: bool = False,
) -> dict[str, int]:
    """Write an exclusive sibling copy; change only the unversioned color block.

    Missing color maps require an explicit XML Drum color template. No template
    instrument, sample, or routing fields are transplanted. Sample resolution
    and hardware acceptance are deliberately not inferred from this operation.
    """
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"source must be a regular, non-symlink XPM: {source}")
    source = source.resolve()
    if destination.suffix.casefold() != '.xpm':
        raise ValueError("colocated output must have an .xpm extension")
    if destination.parent.resolve() != source.parent:
        raise ValueError("colocated output must stay beside the source XPM and its samples")
    if destination.is_symlink() or destination.exists():
        raise FileExistsError(f"refusing to overwrite an existing output or source: {destination}")
    original = source.read_bytes()
    if original.startswith(b'\x1f\x8b'):
        raise ValueError("colocated mode supports XML Drum XPMs only, not compressed programs")
    # Byte-preserving edits below intentionally support UTF-8 XML only.
    original.decode('utf-8-sig')
    if detect_program_type(source) != 'drum':
        raise ValueError("colocated mode requires an XML Drum Program")
    root = ET.fromstring(original)
    program = root.find('Program')
    nodes = program.findall('ProgramPads')
    blocks = PAD_BLOCK.findall(original)
    if len(nodes) > 1 or len(blocks) != len(nodes):
        raise ValueError("ambiguous or unsupported ProgramPads block; source left unchanged")
    prepared = original
    if not nodes:
        if color_template is None:
            raise ValueError("source has no ProgramPads map; supply --color-template with an XML Drum XPM")
        if detect_program_type(color_template) != 'drum':
            raise ValueError("color template must be an XML Drum Program")
        template = ET.parse(color_template).getroot().find('Program')
        template_nodes = template.findall('ProgramPads')
        if len(template_nodes) != 1:
            raise ValueError("color template must contain exactly one ProgramPads map")
        # Reset inherited colors so empty source pads don't inherit template LEDs.
        import json
        import html
        settings = json.loads(html.unescape(template_nodes[0].text or ''))
        settings['ProgramPads']['pads'] = {f'value{i}': 0 for i in range(128)}
        template_nodes[0].text = json.dumps(settings)
        if original.count(b'</Program>') != 1:
            raise ValueError("cannot safely locate the closing Program tag")
        prepared = original.replace(b'</Program>', ET.tostring(template_nodes[0], encoding='utf-8', short_empty_elements=False) + b'</Program>')
    with tempfile.TemporaryDirectory(prefix='mpc-colors-') as folder:
        staging = Path(folder)
        input_path, output_path = staging / 'source.xpm', staging / 'colored.xpm'
        input_path.write_bytes(prepared)
        counts = colorize_drum_program(input_path, output_path, palette, overrides=overrides)
        new_blocks = PAD_BLOCK.findall(output_path.read_bytes())
        if len(new_blocks) != 1:
            raise ValueError("generated color map is ambiguous")
    if blocks:
        result = PAD_BLOCK.sub(lambda _: new_blocks[0], original)
    else:
        result = original.replace(b'</Program>', new_blocks[0] + b'</Program>')
    if PAD_BLOCK.sub(b'', result) != PAD_BLOCK.sub(b'', original):
        raise ValueError("color-only preservation check failed")
    ET.fromstring(result)
    if source.read_bytes() != original:
        raise ValueError("source changed during coloring; no output written")
    if not dry_run:
        # Exclusive creation also refuses a destination created after preflight.
        with destination.open('xb') as stream:
            try:
                stream.write(result)
                stream.flush()
                os.fsync(stream.fileno())
            except BaseException:
                destination.unlink(missing_ok=True)
                raise
    return counts
