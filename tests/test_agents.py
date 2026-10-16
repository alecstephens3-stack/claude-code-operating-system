"""Least privilege, checked by machine rather than promised in a prompt."""
import json
from pathlib import Path

import pytest

import sync_codex

ROOT = Path(__file__).resolve().parent.parent
AGENTS = sorted(p for p in (ROOT / ".claude" / "agents").iterdir() if p.is_dir())
WRITE_TOOLS = {"write", "edit", "multiedit", "notebookedit", "bash"}
READ_ONLY_ROLES = ("-reviewer", "-verifier", "plain-reader")


def front(agent_dir):
    fm, body = sync_codex.parse_frontmatter((agent_dir / "agent.md").read_text())
    return fm, body


def test_there_are_agents():
    assert len(AGENTS) >= 3


def test_no_flat_agent_files():
    assert not list((ROOT / ".claude" / "agents").glob("*.md"))


@pytest.mark.parametrize("agent_dir", AGENTS, ids=lambda p: p.name)
def test_agent_declares_a_narrow_allow_list(agent_dir):
    fm, body = front(agent_dir)
    assert fm.get("name") == agent_dir.name
    assert fm.get("description")
    tools = [t.strip() for t in fm.get("tools", "").split(",") if t.strip()]
    assert tools, "every agent declares its tools"
    assert "*" not in fm["tools"], "no wildcard grants"
    assert body.strip()


@pytest.mark.parametrize("agent_dir", [a for a in AGENTS if a.name.endswith(READ_ONLY_ROLES)],
                         ids=lambda p: p.name)
def test_reviewers_and_verifiers_cannot_write(agent_dir):
    fm, _ = front(agent_dir)
    tools = {t.strip().lower() for t in fm["tools"].split(",")}
    assert not tools & WRITE_TOOLS


def test_security_verifier_has_no_network():
    fm, _ = front(ROOT / ".claude" / "agents" / "skill-security-verifier")
    assert {t.strip() for t in fm["tools"].split(",")} == {"Read", "Grep", "Glob"}


def test_settings_deny_secrets_and_force_push():
    deny = json.loads((ROOT / ".claude" / "settings.json").read_text())["permissions"]["deny"]
    assert "Read(./.env)" in deny
    assert any("push --force" in d for d in deny)
