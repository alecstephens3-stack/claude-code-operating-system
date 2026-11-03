#!/usr/bin/env python3
"""guard_agent_bash.py: a PreToolUse hook that narrows one agent's Bash to the commands it needs.

Agent front matter can grant `Bash` or withhold it, nothing in between. An
agent that reads the books needs to run one read-only script, and an agent that
can run any shell command can also copy what that script prints into a file, a
commit or a request. So the agent gets Bash, and this hook, wired in the
agent's own front matter, allows only the commands listed for it in
agent_commands.json and blocks everything else.

Fail-closed: input it cannot read is blocked, and so is any pipe, redirect,
chaining, substitution or newline, even inside an otherwise allowed command.

    # in .claude/agents/ledger-reader/agent.md
    hooks:
      PreToolUse:
        - matcher: "Bash"
          hooks:
            - type: command
              command: "python3 \"$CLAUDE_PROJECT_DIR/guards/guard_agent_bash.py\" ledger-reader"

Exit 0 allows the command. Exit 2 blocks it, and Claude Code shows the agent
the message on stderr.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parent / "agent_commands.json"
SHELL_META = re.compile(r"[;&|<>`$\\\n]")


def allowed(agent: str, command: str, config: dict) -> tuple[bool, str]:
    rule = config.get(agent)
    if not rule:
        return False, f"no command allow-list for agent {agent!r}, so nothing runs"
    command = command.strip()
    if SHELL_META.search(command):
        return False, "pipes, redirects, chaining and substitution are blocked"
    if not any(re.fullmatch(p, command) for p in rule["allow"]):
        return False, rule["why"]
    return True, ""


def main(argv: list[str] | None = None, stdin=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    agent = argv[0] if argv else ""
    config_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_CONFIG
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        command = json.load(stdin or sys.stdin).get("tool_input", {}).get("command", "")
    except (OSError, ValueError, AttributeError):
        command, config = "", {}
    ok, why = allowed(agent, command, config) if command else (False, "no command to check")
    if ok:
        return 0
    print(f"Blocked for {agent or 'this agent'}: {why}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
