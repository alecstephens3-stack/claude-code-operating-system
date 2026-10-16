#!/usr/bin/env python3
"""handoff.py: hand a task to another operator without leaving this folder.

The problem: one assistant that owns everything carries everything in its
context. Outbound sales work and media production each bring their own
playbooks, memories and tools, and mixed into the main assistant's context
they crowd out the rules that matter there. So each of those jobs is a
separate operator: its own repo, its own CLAUDE.md, its own memory. The owner
still works from one folder. The main assistant hands work over through the
/handoff slash command, which runs this script.

The script starts Claude Code headless (`claude -p`) inside the operator's
repo, so the operator loads its own instructions and none of the main
assistant's. The guardrails for unattended runs live HERE, on the hand-off
channel, as --disallowedTools: an operator run by another agent can draft,
research and build, but it cannot send, publish or delete. When the owner sits
in the operator's repo himself, he keeps full control.

--continue picks up the same operator conversation the last hand-off started,
so answering the operator's questions costs one message, not a fresh start.

    python3 operators/handoff.py outbound "draft three openers for the new list"
    python3 operators/handoff.py outbound --continue "the owner says: skip the last one"
    python3 operators/handoff.py media --dry-run "cut the interview into two clips"
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "operators.json"
SESSION_DIR = Path.home() / ".cache" / "handoff"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def operator(config: dict, name: str) -> dict:
    ops = config["operators"]
    if name not in ops:
        raise SystemExit(f"unknown operator {name!r}. Known: {', '.join(sorted(ops))}")
    op = dict(ops[name])
    op["repo"] = Path(op["repo"]).expanduser()
    return op


def build_command(config: dict, name: str, task: str, prior_session: str | None = None) -> list[str]:
    """The exact claude invocation. Pure, so the guardrails can be tested without running it."""
    op = operator(config, name)
    deny = list(config.get("always_deny", [])) + list(op.get("deny", []))
    cmd = ["claude", "-p", task, "--output-format", "json"]
    if prior_session:
        cmd += ["-r", prior_session]  # -r picks up an earlier session by id
    if deny:
        cmd += ["--disallowedTools", ",".join(deny)]
    return cmd


def session_file(name: str) -> Path:
    return SESSION_DIR / f"{name}-last-session"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a task in another operator's repo.")
    ap.add_argument("operator")
    ap.add_argument("task")
    ap.add_argument("--continue", dest="cont", action="store_true",
                    help="pick up the conversation the last hand-off to this operator started")
    ap.add_argument("--dry-run", action="store_true", help="print the command and stop")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    a = ap.parse_args(argv)

    config = load(Path(a.config))
    op = operator(config, a.operator)
    prior_session = None
    if a.cont:
        sf = session_file(a.operator)
        if not sf.exists():
            raise SystemExit(f"no earlier hand-off to {a.operator} to continue")
        prior_session = sf.read_text().strip()
    cmd = build_command(config, a.operator, a.task, prior_session)

    if a.dry_run:
        print(f"cd {shlex.quote(str(op['repo']))} && {shlex.join(cmd)}")
        return 0
    if not op["repo"].is_dir():
        raise SystemExit(f"{a.operator}'s repo not found at {op['repo']}")

    proc = subprocess.run(cmd, cwd=op["repo"], capture_output=True, text=True)
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(proc.stdout or proc.stderr)
        return proc.returncode or 1
    if result.get("session_id"):
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        session_file(a.operator).write_text(result["session_id"])
    print(result.get("result", ""))
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
