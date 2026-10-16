#!/usr/bin/env python3
"""build_home.py: generate the vault's home page from front matter.

A hand-kept index of notes drifts the first week nobody updates it. So the
home page is part hand-written, part generated: everything between a pair of
markers is rebuilt from the notes in one folder, and everything outside the
markers is left exactly as written.

    <!-- AUTO:projects -->
    (generated list of every note in vault/projects/)
    <!-- /AUTO:projects -->

Notes sort by status (active first, archived last), then by title. A note
whose front matter cannot be read is listed under its file name with a pointer
to the linter, so it never vanishes from the page.

    python3 guards/build_home.py            # rewrite vault/HOME.md
    python3 guards/build_home.py --check    # exit 1 if HOME.md is out of date
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import frontmatter as fmlib  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATUS_ORDER = ["active", "draft", "parked", "shipped", "reference", "archived"]
BLOCK_RE = re.compile(r"(<!-- AUTO:([\w/-]+) -->\n)(.*?)(<!-- /AUTO:\2 -->)", re.DOTALL)


def render_folder(vault: Path, folder: str) -> str:
    base = vault / folder
    if not base.is_dir():
        raise SystemExit(f"HOME.md names a folder that does not exist: {folder}")
    rows = []
    for p in sorted(base.rglob("*.md")):
        rel = p.relative_to(vault).as_posix()
        try:
            fm = fmlib.read(p) or {}
        except fmlib.FrontmatterError:
            fm = {}
        if not fm:
            rows.append((len(STATUS_ORDER), p.stem.lower(),
                         f"- [{p.stem}]({rel}): front matter missing or unreadable, run lint_frontmatter.py"))
            continue
        status = fm.get("status", "")
        rank = STATUS_ORDER.index(status) if status in STATUS_ORDER else len(STATUS_ORDER)
        title = fm.get("title") or p.stem
        summary = fm.get("summary") or ""
        rows.append((rank, str(title).lower(), f"- [{title}]({rel}): {summary} ({status or 'no status'})"))
    if not rows:
        return "_No notes yet._\n"
    return "\n".join(line for _, _, line in sorted(rows)) + "\n"


def build(home_text: str, vault: Path) -> str:
    def replace(m: re.Match) -> str:
        return m.group(1) + render_folder(vault, m.group(2)) + m.group(4)
    return BLOCK_RE.sub(replace, home_text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate the AUTO blocks in HOME.md.")
    ap.add_argument("--vault", default=str(ROOT / "vault"))
    ap.add_argument("--check", action="store_true", help="exit 1 if HOME.md would change")
    a = ap.parse_args(argv)

    vault = Path(a.vault)
    home = vault / "HOME.md"
    current = home.read_text(encoding="utf-8")
    fresh = build(current, vault)
    if a.check:
        if fresh != current:
            print("HOME.md is out of date. Run python3 guards/build_home.py")
            return 1
        print("HOME.md is up to date")
        return 0
    if fresh != current:
        home.write_text(fresh, encoding="utf-8")
        print("HOME.md rebuilt")
    else:
        print("HOME.md already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
