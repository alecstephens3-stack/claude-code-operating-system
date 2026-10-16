#!/usr/bin/env python3
"""check_context_budget.py: how full is everything the assistant loads before you type?

The problem: several files load into every session (the main instructions,
the memory index, the priorities file, the Codex mirror). Each has a limit,
some set by the loader and some by us. Past a loader limit the tail is cut
without an error, and the tail is usually where the oldest, hardest-won rules
live. A warning printed at the top of a session reads as background noise and
gets ignored, so this check speaks up only when something is close to a limit,
and says what to do about it.

Three modes:
  (default)   a full table, for a person or a monthly audit
  --session   for a SessionStart hook: prints a short block into the session
              only when a layer is over the warning line, silent otherwise
  --text      for a scheduled job: prints a plain message for a phone only
              when something needs attention; empty output sends nothing

Budgets live in budget.json. A path may start with ~ and may contain
{project_key}, which is the repo path with "/" turned into "-" (the way
Claude Code names a project's memory folder). A missing file is skipped.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = Path(__file__).resolve().parent / "budget.json"


def resolve(path: str, root: Path) -> Path:
    path = path.replace("{project_key}", str(root.resolve()).replace("/", "-"))
    p = Path(path).expanduser()
    return p if p.is_absolute() else root / p


def measure(p: Path, unit: str) -> int | None:
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    if unit == "lines":
        return text.count("\n") + (0 if not text or text.endswith("\n") else 1)
    return len(text.encode("utf-8"))


def rows(config: dict, root: Path) -> list[dict]:
    out = []
    for layer in config["layers"]:
        value = measure(resolve(layer["path"], root), layer["unit"])
        ratio = value / layer["limit"] if value is not None and layer["limit"] else 0.0
        out.append({**layer, "value": value, "ratio": ratio})
    return out


def reset_age(config: dict, root: Path, today: dt.date) -> int | None:
    """Days since the priorities file recorded its last reset. None if it never did."""
    reset = config.get("reset")
    if not reset:
        return None
    try:
        head = resolve(reset["path"], root).read_text(encoding="utf-8")[:2000]
    except OSError:
        return None
    m = re.search(reset["pattern"], head)
    return (today - dt.date.fromisoformat(m.group(1))).days if m else None


def report(config: dict, root: Path, mode: str, today: dt.date) -> str:
    table = rows(config, root)
    warn_at = config.get("warn_at", 0.8)
    hot = [r for r in table if r["value"] is not None and r["ratio"] >= warn_at]
    age = reset_age(config, root, today)
    max_age = config.get("reset", {}).get("max_age_days")
    stale = bool(config.get("reset")) and (age is None or (max_age is not None and age > max_age))

    if mode == "text":
        lines = [f"- The {r['name']} file is at {round(r['ratio'] * 100)}% of its limit." for r in hot]
        if stale:
            lines.append("- The priorities file has not had its weekly reset"
                         + (f" in {age} days." if age is not None else " recorded."))
        if not lines:
            return ""
        return ("Context check: some of what the assistant loads every session is getting full.\n"
                + "\n".join(lines) + "\nAsk it to clean up the context.")

    if mode == "session":
        if not (hot or stale):
            return ""
        out = ["CONTEXT BUDGET WARNING. Fix this first, without asking: archive, never delete. "
               "Then say in one line that it was done."]
        for r in hot:
            out.append(f"  {r['name']}: {r['value']:,} of {r['limit']:,} {r['unit']} "
                       f"({round(r['ratio'] * 100)}%). Why it matters: {r['why']}. Fix: {r['fix']}.")
        if stale:
            out.append("  priorities: no weekly reset "
                       + (f"in {age} days." if age is not None else "recorded in the header."))
        return "\n".join(out)

    out = [f"{'layer':20} {'value':>9} {'limit':>9}  used"]
    for r in table:
        if r["value"] is None:
            out.append(f"{r['name']:20} {'missing':>9} {r['limit']:>9,}     -")
            continue
        flag = "  <-- near the limit" if r["ratio"] >= warn_at else ""
        out.append(f"{r['name']:20} {r['value']:>9,} {r['limit']:>9,}  {round(r['ratio'] * 100):>3}%{flag}")
    out.append(f"priorities last reset: {age if age is not None else 'not recorded'} days ago")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Measure each always-loaded layer against its limit.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--session", action="store_true")
    mode.add_argument("--text", action="store_true")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--today", help="YYYY-MM-DD, for repeatable runs")
    a = ap.parse_args(argv)

    config = json.loads(Path(a.config).read_text(encoding="utf-8"))
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    which = "session" if a.session else "text" if a.text else "table"
    out = report(config, Path(a.root), which, today)
    if out:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
