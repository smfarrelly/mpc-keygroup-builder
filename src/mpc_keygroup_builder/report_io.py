"""Atomically publish a JSON report without replacing a source file."""

import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


def write_json(
    value: Any, output: Path | None, inputs: tuple[Path, ...] = ()
) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if output is None:
        sys.stdout.write(rendered)
    else:
        requested = output.expanduser()
        if requested.is_symlink():
            raise ValueError(f"report output may not be a symbolic link: {requested}")
        destination = requested.resolve()
        if destination in {path.expanduser().resolve() for path in inputs}:
            raise ValueError(f"report output may not replace an input: {requested}")
        if destination.exists() and not destination.is_file():
            raise ValueError(f"report output is not a regular file: {requested}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", dir=destination.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
                stream.write(rendered)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
