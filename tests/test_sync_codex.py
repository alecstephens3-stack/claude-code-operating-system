import tomllib

import pytest

import sync_codex as sc


@pytest.fixture
def root(tmp_path):
    (tmp_path / "CLAUDE.md").write_text(
        "# CLAUDE.md: Test\n\nSee `.claude/rules/style.md`. Built for Claude Code.\n")
    rules = tmp_path / ".claude" / "rules"
    rules.mkdir(parents=True)
    (rules / "style.md").write_text("# Style\n\n## Dashes\n\nNo dashes.\n")
    (rules / "approvals.md").write_text("# Approvals\n\nDraft, don't send.\n")
    for name, tools in (("reader", "Read, Grep, Glob"), ("writer", "Read, Write, Bash")):
        d = tmp_path / ".claude" / "agents" / name
        d.mkdir(parents=True)
        (d / "agent.md").write_text(
            f'---\nname: {name}\ndescription: The "{name}" agent\ntools: {tools}\n---\n\nBody with """ quotes.\n')
    (tmp_path / ".claude" / "agents" / "loose.md").write_text("a flat file is not an agent")
    cmds = tmp_path / ".claude" / "commands"
    cmds.mkdir()
    (cmds / "handoff.md").write_text("---\ndescription: Hand work over\n---\n\n# /handoff\n\nDo it.\n")
    skill = tmp_path / ".claude" / "skills" / "reset"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: reset\n---\nReset.\n")
    return tmp_path


def test_agents_md_inlines_rules_in_order(root):
    sc.run(root)
    out = (root / "AGENTS.md").read_text()
    assert out.startswith("<!--\nGENERATED FILE")
    assert "# AGENTS.md: Test" in out and "Built for Codex" in out
    assert "the matching rule section below" in out
    assert out.index("## Approvals") < out.index("## Style")
    assert "### Dashes" in out


def test_read_only_agent_gets_read_only_sandbox(root):
    sc.run(root)
    reader = tomllib.loads((root / ".codex" / "agents" / "reader.toml").read_text())
    writer = tomllib.loads((root / ".codex" / "agents" / "writer.toml").read_text())
    assert reader["sandbox_mode"] == "read-only"
    assert "sandbox_mode" not in writer
    assert reader["description"] == 'The "reader" agent'
    assert '"""' in reader["developer_instructions"]


def test_config_lists_only_real_agents(root):
    sc.run(root)
    config = tomllib.loads((root / ".codex" / "config.toml").read_text())
    assert sorted(config["agents"]) == ["reader", "writer"]
    assert config["agents"]["reader"]["config_file"] == "agents/reader.toml"


def test_commands_and_skills_are_mirrored(root):
    sc.run(root)
    skill = (root / ".agents" / "skills" / "handoff" / "SKILL.md").read_text()
    assert skill.startswith("---\nname: handoff\ndescription: Hand work over\n---")
    assert (root / ".agents" / "skills" / "reset" / "SKILL.md").read_text() == "---\nname: reset\n---\nReset.\n"


def test_idempotent_and_check_mode(root):
    assert sc.run(root).changes
    assert sc.run(root).changes == []
    assert sc.main(["--root", str(root), "--check"]) == 0
    (root / ".claude" / "rules" / "style.md").write_text("# Style\n\nChanged.\n")
    before = (root / "AGENTS.md").read_text()
    assert sc.main(["--root", str(root), "--check"]) == 1
    assert (root / "AGENTS.md").read_text() == before


def test_orphans_reported_and_pruned(root):
    sc.run(root)
    (root / ".codex" / "agents" / "ghost.toml").write_text("x")
    (root / ".agents" / "skills" / "ghost").mkdir()
    s = sc.run(root)
    assert len(s.orphans) == 2
    sc.run(root, prune=True)
    assert not (root / ".codex" / "agents" / "ghost.toml").exists()
    assert not (root / ".agents" / "skills" / "ghost").exists()
