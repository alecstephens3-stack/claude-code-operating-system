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


def test_design_system_hook_is_wired():
    hooks = json.loads((ROOT / ".claude" / "settings.json").read_text())["hooks"]["PostToolUse"]
    commands = [h["command"] for group in hooks for h in group["hooks"]]
    assert any("check_design_system.py" in c for c in commands)


ALLOWED_MODELS = {"opus", "sonnet"}


@pytest.mark.parametrize("agent_dir", AGENTS, ids=lambda p: p.name)
def test_agent_pins_a_model_at_or_above_the_floor(agent_dir):
    fm, _ = front(agent_dir)
    assert fm.get("model") in ALLOWED_MODELS, "the smallest model missed too much in review work"


@pytest.mark.parametrize("agent_dir", AGENTS, ids=lambda p: p.name)
def test_mcp_grants_name_single_tools(agent_dir):
    fm, _ = front(agent_dir)
    for tool in (t.strip() for t in fm["tools"].split(",")):
        if tool.startswith("mcp__"):
            assert tool.count("__") == 2 and not tool.endswith("*"), f"{tool} grants a whole server"


COMMANDS = json.loads((ROOT / "guards" / "agent_commands.json").read_text())


@pytest.mark.parametrize("agent_dir", AGENTS, ids=lambda p: p.name)
def test_any_agent_with_bash_is_held_by_a_command_guard(agent_dir):
    fm, _ = front(agent_dir)
    tools = {t.strip() for t in fm["tools"].split(",")}
    if "Bash" not in tools:
        return
    raw = (agent_dir / "agent.md").read_text()
    head = raw[:raw.find("\n---\n", 4)]
    assert "PreToolUse" in head and f"guard_agent_bash.py\\\" {agent_dir.name}" in head
    assert agent_dir.name in COMMANDS, "the guard needs an allow-list entry for this agent"


def test_hooked_agent_is_read_only_on_the_codex_side():
    toml = (ROOT / ".codex" / "agents" / "ledger-reader.toml").read_text()
    assert 'sandbox_mode = "read-only"' in toml
