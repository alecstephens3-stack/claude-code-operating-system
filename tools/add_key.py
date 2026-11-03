#!/usr/bin/env python3
"""add_key.py: put a key or password into .env without it passing through the chat.

When the assistant needs a secret, the easy path is to ask for it in the chat,
and then the value sits in a transcript. Instead the assistant runs:

    python3 tools/add_key.py REPORT_API_KEY "reporting API key"

A macOS password dialog opens on the owner's screen. Whatever is pasted is
written to .env (replacing an older value for that name) with mode 600, and
the script prints only the name and the length. Cancel or an empty box saves
nothing and exits 1.

I used a system dialog rather than a local web page on purpose: browser
extensions, including the assistant's own browser tools, can read a page's
form fields, and a page needs a local server. The dialog sits outside both.

--preview shows the dialog and throws the answer away.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

ENV = Path(__file__).resolve().parent.parent / ".env"
NAME = re.compile(r"[A-Z][A-Z0-9_]*")


def ask_macos(label: str) -> str | None:
    prompt = f"Paste your {label}.\\n\\nIt is saved on this Mac only and never shown in the chat."
    script = (f'display dialog "{prompt}" default answer "" with hidden answer '
              'with title "Add a key" buttons {"Cancel", "Save"} default button "Save"')
    out = subprocess.run(["osascript", "-e", script, "-e", "text returned of result"],
                         capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else None


def upsert(env: Path, name: str, value: str) -> bool:
    """Write NAME=value into env, replacing an existing line. True if it replaced one."""
    lines = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith(f"{name}="):
            lines[i] = f"{name}={value}"
            replaced = True
    if not replaced:
        lines.append(f"{name}={value}")
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")
    env.chmod(0o600)
    return replaced


def main(argv: list[str] | None = None, ask: Callable[[str], str | None] = ask_macos,
         env: Path = ENV) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--preview"]:
        ask(argv[1] if len(argv) > 1 else "key")
        print("Preview only, nothing saved.")
        return 0
    if not argv or not NAME.fullmatch(argv[0]):
        print("usage: add_key.py NAME [label]   (NAME in CAPS_WITH_UNDERSCORES)", file=sys.stderr)
        return 2
    name = argv[0]
    value = ask(argv[1] if len(argv) > 1 else name)
    if not value:
        print("Cancelled or empty, nothing saved.", file=sys.stderr)
        return 1
    replaced = upsert(env, name, value)
    print(f"{name} {'updated' if replaced else 'saved'} in .env ({len(value)} characters).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
