#!/usr/bin/env python3
"""guard_secret_commit.py: a git pre-commit hook that blocks keys and bank details in staged changes.

The project settings already deny the assistant reads of .env, but a value can
still reach a commit another way: pasted into a note, printed into a log the
assistant then saves, or copied into a test. This scans every ADDED line of
the staged diff for:

  - the literal value of any secret in the repo's .env (12 characters or more)
  - common key shapes: model API keys, cloud access keys, git host tokens,
    bank-link access tokens, private key headers
  - an account line in the shape a bank tool prints: account type, three
    dots, last four digits

Git does not version hooks, so after a fresh clone install it again:

    python3 guards/guard_secret_commit.py --install

Exit 1 blocks the commit and names the file and what was found, never the value.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PATTERNS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"), "a model API key"),
    (re.compile(r"\bsk-[A-Za-z0-9]{32,}"), "a model API key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "a cloud access key id"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}"), "a git host token"),
    (re.compile(r"\baccess-(?:production|sandbox|development)-[0-9a-f-]{8,}"), "a bank-link access token"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "a private key"),
    (re.compile(r"\b(?:Checking|Savings|Credit Card|Money Market)\s+\.\.\.\d{4}\b", re.I), "a bank account line"),
]


def env_secrets(env: Path) -> list[str]:
    out = []
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                value = line.split("=", 1)[1].strip().strip("'\"")
                if len(value) >= 12:
                    out.append(value)
    return out


def scan(diff: str, literals: list[str]) -> list[tuple[str, str]]:
    hits, current = set(), "?"
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else line[4:]
            continue
        if not line.startswith("+"):
            continue
        if any(lit in line for lit in literals):
            hits.add((current, "a value from .env"))
        for rx, what in PATTERNS:
            if rx.search(line):
                hits.add((current, what))
    return sorted(hits)


def install(root: Path) -> Path:
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text('#!/bin/sh\nexec python3 "$(git rev-parse --show-toplevel)/guards/guard_secret_commit.py"\n')
    hook.chmod(0o755)
    return hook


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--install" in argv:
        print(f"installed {install(ROOT)}")
        return 0
    diff = subprocess.run(["git", "diff", "--cached", "-U0", "--no-color"], cwd=ROOT,
                          capture_output=True, text=True).stdout
    hits = scan(diff, env_secrets(ROOT / ".env"))
    if not hits:
        return 0
    print("Commit blocked: secrets or bank details in the staged changes.", file=sys.stderr)
    for path, what in hits:
        print(f"  {path}: {what}", file=sys.stderr)
    print("Remove them, keep the value in .env, and commit again.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
