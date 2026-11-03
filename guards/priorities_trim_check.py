#!/usr/bin/env python3
"""priorities_trim_check.py: after trimming the priorities file, list what only the archive still has.

The weekly reset copies the old priorities file to the archive verbatim, then
cuts the live file down to what is still open. The first time I trimmed by
hand, four open items went with the history: an unbuilt fix, a pointer to the
last call's notes, a signed contract and a retest date. Nothing in the trimmed
file was wrong, things were just missing, and missing is the hardest kind of
error to see by reading.

So after a trim this compares the two files on the things that are easy to
lose and expensive to forget: ticket ids, file pointers, email addresses,
money amounts and links. Each one printed is either finished (fine to leave
in the archive) or still open (put it back).

    python3 guards/priorities_trim_check.py vault/archives/priorities-2026-10-05.md vault/priorities.md

Exit 0 when nothing was dropped, 1 when there is something to confirm.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PATTERNS = {
    "tickets": r"\b[A-Z]{2,6}-\d+\b",
    "files": r"[\w./-]+\.(?:md|html|pdf|py|json|csv|zip)\b",
    "emails": r"[\w.+-]+@[\w-]+\.[\w.]+\w",
    "money": r"\$[\d,.]*\d",
    "links": r"https?://[^\s)`>]+[^\s).,`>]",
}


def dropped(old: str, new: str) -> dict[str, list[str]]:
    out = {}
    for kind, pattern in PATTERNS.items():
        gone = sorted(set(re.findall(pattern, old)) - set(re.findall(pattern, new)))
        if gone:
            out[kind] = gone
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="List what a priorities trim removed from the live file.")
    ap.add_argument("archive", help="the verbatim copy taken before the trim")
    ap.add_argument("live", nargs="?", default="vault/priorities.md")
    a = ap.parse_args(argv)
    gone = dropped(Path(a.archive).read_text(encoding="utf-8"), Path(a.live).read_text(encoding="utf-8"))
    for kind, items in gone.items():
        print(f"{kind} only in the archive: {', '.join(items)}")
    total = sum(len(v) for v in gone.values())
    print(f"{total} item(s) to confirm as finished, or put back" if total else "nothing dropped")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
