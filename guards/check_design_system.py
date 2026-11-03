#!/usr/bin/env python3
"""check_design_system.py: a PostToolUse hook that blocks new pages built off the design system.

Two failures it was built for. First, a session was asked for "the design
system, but blue". It listed the design system folder, read none of it, wrote
a few hundred lines of CSS by hand, and its own summary said the system's
structure "is kept". Two always-loaded rules already said to build from the
kit. Second, a few weeks later, a private prep page went out on hand-written
CSS with an opt-out comment the session wrote for itself: "private, not a
client deliverable". Rules had failed twice, so this checks the file instead.

A new HTML document that styles itself must carry the kit's fingerprint (the
DS:KIT marker, a ds- class, a --ds- token) or an opt-out that names one of a
fixed set of categories. "Private", "internal" and "no time" are not on the
list. It also fails a page that carries the retired v1 values, since v1 used
the same token prefix and would otherwise pass, and a page that inlines a logo
mark that is not the canonical one (a redrawn mark spreads by copy and paste).

Only new files are judged: a page already in HEAD is history, and asking for a
migration on every edit is how a guard gets switched off. It fails open on
anything it cannot parse, so it never blocks unrelated work.

    <!-- DS:NONE client-brand: this is the client's own look -->

Rules live in design_system.json. Exit 2 sends the message back to the model.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = Path(__file__).resolve().parent / "design_system.json"


def opt_out_res(cfg: dict) -> tuple[re.Pattern, re.Pattern]:
    cats = [c for c in cfg["opt_out_categories"] if c != "owner-approved"]
    valid = re.compile(r"DS:NONE\s+(?:" + "|".join(map(re.escape, cats))
                       + r"|owner-approved\s+\d{4}-\d{2}-\d{2})\s*:")
    return valid, re.compile(r"DS:NONE(?![-\w])[^>]*")


def judge(text: str, rel: str, cfg: dict) -> str | None:
    """The reason to block this page, or None. `rel` is the path inside the repo."""
    if any(part in cfg["skip_dirs"] for part in Path(rel).parts):
        return None
    if rel.startswith(tuple(cfg.get("exempt_paths", []))):
        return None
    low = text.lower()
    if "<html" not in low or ("<style" not in low and "stylesheet" not in low):
        return None  # fragments and templates are judged where they are assembled

    logo = cfg.get("logo")
    if logo:
        fake = any(sig in text for sig in logo["known_fakes"])
        wrong = logo["mark_class"] in text and "<svg" in low and logo["canonical_signature"] not in text
        if fake or wrong:
            return ("this page inlines a logo mark that is not the canonical one. "
                    "Copy the mark from the design system's logo snippet; never redraw it.")

    valid, any_opt_out = opt_out_res(cfg)
    if valid.search(text):
        return None
    attempt = any_opt_out.search(text)
    if attempt:
        cats = ", ".join(cfg["opt_out_categories"])
        return (f"the opt-out {attempt.group(0).strip()[:80]!r} names no recognised category. "
                f"Use one of: {cats}. Private, internal and short on time are not categories.")

    found = [r["why"] for r in cfg.get("retired", []) if re.search(r["pattern"], text, re.I)]
    if found:
        return "this page carries the retired v1 system: " + "; ".join(found) + ". Build it from the current kit."

    if re.search(cfg["fingerprint"], text):
        return None
    css = sum(len(b.splitlines()) for b in re.findall(r"<style[^>]*>(.*?)</style>", text, re.S | re.I))
    return (f"this page carries none of the design system's fingerprint and has {css} lines of "
            "hand-written CSS. Build it from the kit (start from the starter page, keep the DS:KIT "
            "markers), or opt out with <!-- DS:NONE <category>: why -->.")


def in_head(path: Path, root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
        return subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"HEAD:{rel}"],
                              capture_output=True, timeout=5).returncode == 0
    except (ValueError, OSError, subprocess.SubprocessError):
        return False


def main(stdin=None, root: Path = ROOT, config: Path = DEFAULT_CONFIG) -> int:
    try:
        payload = json.load(stdin or sys.stdin)
        fp = (payload.get("tool_input") or {}).get("file_path") or ""
        path = Path(fp)
        if path.suffix.lower() not in (".html", ".htm"):
            return 0
        rel = path.resolve().relative_to(root.resolve()).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        cfg = json.loads(config.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - fail open: never block work this guard cannot judge
        return 0
    if in_head(path, root):
        return 0
    reason = judge(text, rel, cfg)
    if reason is None:
        return 0
    print(f"DESIGN SYSTEM GUARD ({rel}): {reason}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
