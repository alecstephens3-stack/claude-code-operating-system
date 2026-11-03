#!/usr/bin/env python3
"""open_checklist.py: put a list of steps for the owner in the browser, where he can tick them off.

Steps the owner has to do himself (a console sign-in, a settings page, a form)
used to arrive as a numbered list in the chat. He reads the chat on one screen
and clicks on another, a long list scrolls away, and there is nowhere to tick.
So every list of steps for him becomes a small page instead: one card per step,
a tick box that survives a reload, and a Copy button beside anything he has to
paste (a form answer, a URL), so nothing gets retyped by hand.

    python3 tools/open_checklist.py steps.json
    echo '{...}' | python3 tools/open_checklist.py -
    python3 tools/open_checklist.py steps.json --no-open    # write the page only

steps.json:
    {"id": "dns-records", "title": "Point the domain at the new host",
     "intro": "About ten minutes.",
     "steps": [{"text": "Open the DNS settings", "detail": "At the registrar.",
                "copy": "https://registrar.example.com/dns"}]}

The page is written to artifacts/checklists/<id>.html. The same id reopens the
same ticks.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).resolve().parent / "checklist_template.html"
OUT_DIR = ROOT / "artifacts" / "checklists"
ID = re.compile(r"[a-z0-9][a-z0-9-]{0,80}")


class SpecError(ValueError):
    pass


def render(spec: dict, today: dt.date | None = None, template: Path = TEMPLATE) -> str:
    cid = spec.get("id", "")
    if not ID.fullmatch(cid):
        raise SpecError(f"bad id {cid!r}: lowercase letters, digits and hyphens only")
    steps = spec.get("steps") or []
    if not steps:
        raise SpecError("no steps")
    items = []
    for i, s in enumerate(steps, 1):
        li = (f'    <li class="ds-step" data-id="s{i}"><label><input type="checkbox">'
              f'<span class="ds-text">{html.escape(s["text"])}</span></label>')
        if s.get("detail"):
            li += f'<p class="ds-detail">{html.escape(s["detail"])}</p>'
        if s.get("copy"):
            li += f'<div class="ds-copy"><code>{html.escape(s["copy"])}</code><button type="button">Copy</button></div>'
        items.append(li + "</li>")
    d = today or dt.date.today()
    page = (template.read_text(encoding="utf-8")
            .replace("{{TITLE}}", html.escape(spec.get("title", cid)))
            .replace("{{INTRO}}", html.escape(spec.get("intro", "")))
            .replace("{{CHECKLIST_ID}}", cid)
            .replace("{{CREATED}}", f"{d.day} {d:%b %Y}")
            .replace("{{ITEMS}}", "\n".join(items)))
    if "{{" in page:
        raise SpecError("a template placeholder was left unfilled")
    return page


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write a checklist page and open it in the browser.")
    ap.add_argument("spec", help="steps JSON file, or - for stdin")
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args(argv)
    raw = sys.stdin.read() if a.spec == "-" else Path(a.spec).read_text(encoding="utf-8")
    try:
        spec = json.loads(raw)
        page = render(spec)
    except (ValueError, KeyError) as e:
        print(f"open_checklist: {e}", file=sys.stderr)
        return 2
    out = Path(a.out) / f"{spec['id']}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    if not a.no_open:
        webbrowser.open(out.resolve().as_uri())
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
