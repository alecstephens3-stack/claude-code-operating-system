#!/usr/bin/env python3
"""lint_frontmatter.py: the mechanical half of a vault health check.

The vault is plain markdown, and every tool that reads it (the generated home
page, table views, the assistant itself) depends on each note carrying the same
front matter fields. A script can check those fields every time, so a person
(or the assistant's lint skill) only has to make the judgment calls.

ERROR lines fail the run:
  MISSING      no front matter block at all
  UNPARSEABLE  a block exists but cannot be read (usually an unquoted colon)
  FIELD        a required field is absent or empty
  TYPE         `type` is not one of the schema's types
  STATUS       `status` is not one of the schema's statuses
  DATE         a date field is not an ISO date (YYYY-MM-DD)
  TAGS         `tags` is not a list
  LINK         a [[wikilink]] points at a note that does not exist

WARN lines never fail the run:
  STALE        an active note has not been updated in a long time
  SUMMARY      the summary ends with a period (the home page adds its own)

The schema lives in vault_schema.json next to this file. It is the single
source of truth; docs/vault-schema.md explains it and does not restate it.

    python3 guards/lint_frontmatter.py                 # lint ./vault
    python3 guards/lint_frontmatter.py path/to/vault --today 2026-12-01
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import frontmatter as fmlib  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA = Path(__file__).resolve().parent / "vault_schema.json"
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_schema(path: Path = DEFAULT_SCHEMA) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_note(path: Path, rel: str, schema: dict, today: dt.date,
               known_stems: set[str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    text = path.read_text(encoding="utf-8")
    try:
        fm = fmlib.parse(text)
    except fmlib.FrontmatterError as exc:
        return [f"UNPARSEABLE {rel}: {exc}"], warns
    if fm is None:
        return [f"MISSING     {rel}: no front matter block"], warns

    for field in schema["required"]:
        if fm.get(field) in (None, "", []):
            errors.append(f"FIELD       {rel}: missing {field!r}")

    kind = fm.get("type")
    if kind and kind not in schema["types"]:
        errors.append(f"TYPE        {rel}: {kind!r} is not one of {sorted(schema['types'])}")
    elif kind:
        for field in schema["types"][kind]:
            if fm.get(field) in (None, "", []):
                errors.append(f"FIELD       {rel}: type {kind!r} needs {field!r}")

    status = fm.get("status")
    if status and status not in schema["statuses"]:
        errors.append(f"STATUS      {rel}: {status!r} is not one of {schema['statuses']}")

    for field in schema.get("date_fields", []):
        value = fm.get(field)
        if value and (not isinstance(value, str) or not ISO_RE.match(value)):
            errors.append(f"DATE        {rel}: {field} {value!r} is not YYYY-MM-DD")

    if "tags" in fm and not isinstance(fm["tags"], list):
        errors.append(f"TAGS        {rel}: tags must be a list, like [project, forms]")

    summary = fm.get("summary")
    if isinstance(summary, str) and summary.endswith("."):
        warns.append(f"SUMMARY     {rel}: summary ends with a period")

    updated = fm.get("last-updated")
    if status == "active" and isinstance(updated, str) and ISO_RE.match(updated):
        age = (today - dt.date.fromisoformat(updated)).days
        if age > schema.get("stale_after_days", 90):
            warns.append(f"STALE       {rel}: active but last updated {age} days ago")

    _, body = fmlib.split(text)
    for target in WIKILINK_RE.findall(body):
        stem = Path(target.strip()).stem.lower()
        if stem not in known_stems:
            errors.append(f"LINK        {rel}: [[{target.strip()}]] points at no note")
    return errors, warns


def lint(vault: Path, schema: dict, today: dt.date) -> tuple[list[str], list[str]]:
    paths = fmlib.notes(vault, set(schema.get("skip_dirs", [])))
    known = {p.stem.lower() for p in paths}
    errors: list[str] = []
    warns: list[str] = []
    for p in paths:
        e, w = check_note(p, str(p.relative_to(vault)), schema, today, known)
        errors += e
        warns += w
    return errors, warns


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check every vault note's front matter.")
    ap.add_argument("vault", nargs="?", default=str(ROOT / "vault"))
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    ap.add_argument("--today", help="YYYY-MM-DD, for repeatable stale checks")
    ap.add_argument("--quiet", action="store_true",
                    help="print only errors, and nothing at all when clean (for scheduled jobs)")
    a = ap.parse_args(argv)

    vault = Path(a.vault)
    if not vault.is_dir():
        print(f"vault not found: {vault}")
        return 2
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    schema = load_schema(Path(a.schema))
    errors, warns = lint(vault, schema, today)
    if a.quiet:
        if errors:
            print(f"Vault lint found {len(errors)} problem(s):")
            for line in errors:
                print("  " + line)
        return 1 if errors else 0
    count = len(fmlib.notes(vault, set(schema.get("skip_dirs", []))))
    print(f"lint_frontmatter: {count} notes, {len(errors)} error(s), {len(warns)} warning(s)")
    for line in errors:
        print("  ERROR " + line)
    for line in warns:
        print("  WARN  " + line)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
