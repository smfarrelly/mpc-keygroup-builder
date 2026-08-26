"""Stable recursive comparison helpers for MPC JSON-like structures."""

from __future__ import annotations

from typing import Any


def pointer_token(value: object) -> str:
    return str(value).replace("~", "~0").replace("/", "~1")


def compare(before: Any, after: Any, path: str = "") -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    if type(before) is not type(after):
        return [{"path": path or "/", "kind": "type", "before": before, "after": after}]
    if isinstance(before, dict):
        for key in sorted(set(before) | set(after), key=str):
            child = f"{path}/{pointer_token(key)}"
            if key not in before:
                changes.append({"path": child, "kind": "added", "after": after[key]})
            elif key not in after:
                changes.append({"path": child, "kind": "removed", "before": before[key]})
            else:
                changes.extend(compare(before[key], after[key], child))
        return changes
    if isinstance(before, list):
        for index in range(max(len(before), len(after))):
            child = f"{path}/{index}"
            if index >= len(before):
                changes.append({"path": child, "kind": "added", "after": after[index]})
            elif index >= len(after):
                changes.append({"path": child, "kind": "removed", "before": before[index]})
            else:
                changes.extend(compare(before[index], after[index], child))
        return changes
    if before != after:
        changes.append({"path": path or "/", "kind": "changed", "before": before, "after": after})
    return changes
