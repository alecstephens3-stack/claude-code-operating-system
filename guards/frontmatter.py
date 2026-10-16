"""Small front matter reader shared by the vault guards.

A vault note opens with a block like this:

    ---
    type: project
    title: Intake form rebuild
    tags: [project, forms]
    ---

This module reads the subset of YAML that notes actually use: `key: value`,
`key: [a, b]` and quoted strings. Anything outside that subset is reported as
an error instead of guessed at. A block that half-parses is worse than one
that fails, because the note drops off the generated home page and nobody
notices. The classic case is an unquoted colon inside a title
("title: Call notes: pricing"), which full YAML reads as a nested key.

No third-party dependencies, so every guard runs on a stock Python.
"""
from __future__ import annotations

import re
from pathlib import Path

KEY_RE = re.compile(r"^([A-Za-z][\w-]*):(?:[ \t]+(.*))?$")


class FrontmatterError(ValueError):
    """The note has a front matter block, but it cannot be read safely."""


def split(text: str) -> tuple[list[str] | None, str]:
    """Return (block_lines, body). block_lines is None when there is no block."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    raise FrontmatterError("front matter block is never closed with ---")


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_value(raw: str, key: str) -> str | list[str]:
    raw = (raw or "").strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        return [_unquote(item.strip()) for item in inner.split(",") if item.strip()] if inner else []
    if raw and raw[0] in "\"'":
        if len(raw) < 2 or raw[-1] != raw[0]:
            raise FrontmatterError(f"{key}: quote is never closed")
        return raw[1:-1]
    if " #" in raw:
        raw = raw.split(" #", 1)[0].rstrip()
    if ": " in raw or raw.endswith(":"):
        raise FrontmatterError(
            f"{key}: unquoted colon in the value. Wrap the value in double quotes")
    return raw


def parse(text: str) -> dict | None:
    """Parse a note's front matter. None means the note has no block at all."""
    block, _ = split(text)
    if block is None:
        return None
    data: dict = {}
    for n, line in enumerate(block, start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1] in " \t":
            raise FrontmatterError(f"line {n}: nested or indented values are not supported")
        m = KEY_RE.match(line)
        if not m:
            raise FrontmatterError(f"line {n}: expected 'key: value', got {line.strip()[:60]!r}")
        key = m.group(1)
        if key in data:
            raise FrontmatterError(f"line {n}: duplicate key {key!r}")
        data[key] = parse_value(m.group(2) or "", key)
    return data


def read(path: Path) -> dict | None:
    return parse(path.read_text(encoding="utf-8"))


def notes(vault: Path, skip_dirs: set[str] | frozenset[str] = frozenset()) -> list[Path]:
    """Every markdown note under the vault, minus skipped folders, in a stable order."""
    out = []
    for p in sorted(vault.rglob("*.md")):
        rel = p.relative_to(vault)
        if any(part in skip_dirs or part.startswith(".") for part in rel.parts[:-1]):
            continue
        out.append(p)
    return out
