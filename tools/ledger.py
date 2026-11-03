#!/usr/bin/env python3
"""ledger.py: read-only answers from a bookkeeping export, for the ledger-reader agent.

It reads a CSV export (date, account, payee, amount, memo) and prints answers
for the chat. It never writes a file and never calls the network. The agent
that runs it is held to these three commands by guards/guard_agent_bash.py.

    python3 tools/ledger.py summary            # balance per account
    python3 tools/ledger.py recent 30          # the last 30 days, newest first
    python3 tools/ledger.py find "northside"   # has a payment from them landed?

LEDGER_CSV points at the export. The default is the fictional examples/ledger.csv.
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "examples" / "ledger.csv"


def load(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["amount"] = float(r["amount"])
        r["date"] = dt.date.fromisoformat(r["date"])
    return rows


def summary(rows: list[dict]) -> list[str]:
    totals: dict[str, float] = defaultdict(float)
    for r in rows:
        totals[r["account"]] += r["amount"]
    return [f"{acct}: {total:,.2f}" for acct, total in sorted(totals.items())]


def recent(rows: list[dict], days: int, today: dt.date) -> list[str]:
    since = today - dt.timedelta(days=days)
    hits = sorted((r for r in rows if r["date"] >= since), key=lambda r: r["date"], reverse=True)
    return [f"{r['date']}  {r['payee']:<24} {r['amount']:>10,.2f}  {r['account']}" for r in hits]


def find(rows: list[dict], text: str) -> list[str]:
    t = text.lower()
    hits = [r for r in rows if t in r["payee"].lower() or t in r["memo"].lower()]
    return [f"{r['date']}  {r['payee']:<24} {r['amount']:>10,.2f}  {r['memo']}" for r in hits] or [
        f"nothing matching {text!r}"]


def main(argv: list[str] | None = None, today: dt.date | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    rows = load(Path(os.environ.get("LEDGER_CSV", DEFAULT)))
    cmd = argv[0] if argv else "summary"
    if cmd == "summary":
        out = summary(rows)
    elif cmd == "recent" and len(argv) == 2 and argv[1].isdigit():
        out = recent(rows, int(argv[1]), today or dt.date.today())
    elif cmd == "find" and len(argv) >= 2:
        out = find(rows, " ".join(argv[1:]))
    else:
        print(__doc__, file=sys.stderr)
        return 2
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
