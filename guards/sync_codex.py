#!/usr/bin/env python3
"""sync_codex.py: keep the Codex side of the project generated from the Claude side.

The problem: the same project is opened by two coding agents, Claude Code and
Codex, and each reads its own files. Two hand-kept copies of the same
instructions disagree within a week. So the Claude side is the only source of
truth and the Codex side is a one-way mirror, rebuilt by this script:

  CLAUDE.md + .claude/rules/*.md        ->  AGENTS.md
  .claude/agents/<name>/agent.md        ->  .codex/agents/<name>.toml
                                            .codex/config.toml ([agents.*] table)
  .claude/commands/<name>.md            ->  .agents/skills/<name>/SKILL.md
  .claude/skills/<name>/                ->  .agents/skills/<name>/ (file copy)

Least privilege carries across. Codex agent files have no per-tool allow-list,
but they do have a per-agent sandbox. An agent whose Claude `tools:` list holds
no write or shell tool gets `sandbox_mode = "read-only"` on the Codex side.

Idempotent: a second run with no source changes writes nothing.

    python3 guards/sync_codex.py           # regenerate
    python3 guards/sync_codex.py --check   # exit 1 if anything is out of date
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WRITE_TOOLS = {"write", "edit", "multiedit", "notebookedit", "bash"}
HEADER = ("<!--\nGENERATED FILE. Do not edit by hand.\n"
          "Edit CLAUDE.md or .claude/rules/*.md, then run python3 guards/sync_codex.py\n-->\n")
PATH_SUBS = [
    (r"`\.claude/agents/([\w-]+)/agent\.md`", r"`.codex/agents/\1.toml`"),
    (r"`\.claude/commands/", "`.agents/skills/"),
    (r"`\.claude/rules/[\w-]+\.md`", "the matching rule section below"),
    (r"Claude Code", "Codex"),
]


class Sync:
    def __init__(self, root: Path, check: bool):
        self.root = root
        self.check = check
        self.changes: list[str] = []
        self.orphans: list[str] = []

    def write(self, rel: str, content: str) -> None:
        path = self.root / rel
        if path.exists() and path.read_text(encoding="utf-8") == content:
            return
        self.changes.append(rel)
        if not self.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Flat `key: value` front matter, as agent and command files use it."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    data = {}
    for line in text[4:end].split("\n"):
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if m:
            data[m.group(1)] = m.group(2).strip()
    return data, text[end + 5:]


def subs(text: str) -> str:
    for pattern, repl in PATH_SUBS:
        text = re.sub(pattern, repl, text)
    return text


def toml_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def toml_block(value: str) -> str:
    return '"""\n' + value.replace("\\", "\\\\").replace('"""', '\\"\\"\\"') + '\n"""'


def compose_agents_md(root: Path) -> str:
    claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
    claude = re.sub(r"^# CLAUDE\.md\b", "# AGENTS.md", claude, count=1)
    parts = [HEADER, subs(claude).rstrip() + "\n"]
    rules = sorted((root / ".claude" / "rules").glob("*.md"))
    if rules:
        parts.append("\n---\n")
    for rule in rules:
        lines = rule.read_text(encoding="utf-8").split("\n")
        title = rule.stem.replace("-", " ").capitalize()
        if lines and lines[0].startswith("# "):
            title, lines = lines[0][2:].strip(), lines[1:]
        body = "\n".join("#" + line if line.startswith("## ") else line for line in lines)
        parts.append(f"\n## {title} (inlined from .claude/rules/{rule.name})\n")
        parts.append(subs(body).rstrip() + "\n")
    return "".join(parts)


def restrictions(fm: dict) -> list[str]:
    tools = {t.strip().lower() for t in fm.get("tools", "").split(",") if t.strip()}
    lines = ["# least privilege, carried over from the Claude agent's tools list"]
    if tools and not tools & WRITE_TOOLS:
        lines.append('sandbox_mode = "read-only"')
    else:
        lines.append("# sandbox: inherits the session default (the Claude agent can write)")
    if tools and not any(t.startswith("mcp__") for t in tools):
        lines.append("# no MCP servers: the Claude tools list grants none")
    lines.append(f"# Claude tools: {fm.get('tools', '(none listed)')}")
    return lines


def sync_agents(s: Sync) -> None:
    src = s.root / ".claude" / "agents"
    names: dict[str, str] = {}
    for agent_dir in sorted(p for p in src.iterdir() if p.is_dir()) if src.exists() else []:
        agent_file = agent_dir / "agent.md"
        if not agent_file.exists():
            continue
        fm, body = parse_frontmatter(agent_file.read_text(encoding="utf-8"))
        name = agent_dir.name
        names[name] = fm.get("description", "")
        s.write(f".codex/agents/{name}.toml", "\n".join([
            f"# GENERATED from .claude/agents/{name}/agent.md by guards/sync_codex.py",
            "",
            f"name = {toml_str(name)}",
            f"description = {toml_str(fm.get('description', ''))}",
            'model_reasoning_effort = "medium"',
            "",
            *restrictions(fm),
            "",
            f"developer_instructions = {toml_block(subs(body.strip()))}",
            "",
        ]))
    config = ["# GENERATED by guards/sync_codex.py from .claude/agents/*/agent.md", ""]
    for name, desc in sorted(names.items()):
        config += [f"[agents.{name}]", f"description = {toml_str(desc)}",
                   f'config_file = "agents/{name}.toml"', ""]
    if names:
        s.write(".codex/config.toml", "\n".join(config))
    out = s.root / ".codex" / "agents"
    for toml in sorted(out.glob("*.toml")) if out.exists() else []:
        if toml.stem not in names:
            s.orphans.append(f".codex/agents/{toml.name} has no source agent")


def sync_skills(s: Sync) -> None:
    expected: set[str] = set()
    commands = s.root / ".claude" / "commands"
    for cmd in sorted(commands.glob("*.md")) if commands.exists() else []:
        fm, body = parse_frontmatter(cmd.read_text(encoding="utf-8"))
        desc = fm.get("description") or f"Mirror of /{cmd.stem}"
        expected.add(cmd.stem)
        s.write(f".agents/skills/{cmd.stem}/SKILL.md",
                f"---\nname: {cmd.stem}\ndescription: {desc}\n---\n"
                f"<!-- GENERATED from .claude/commands/{cmd.name} by guards/sync_codex.py -->\n\n"
                + subs(body.lstrip()))
    skills = s.root / ".claude" / "skills"
    for skill_dir in sorted(p for p in skills.iterdir() if p.is_dir()) if skills.exists() else []:
        expected.add(skill_dir.name)
        for f in sorted(skill_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(skill_dir).as_posix()
                s.write(f".agents/skills/{skill_dir.name}/{rel}", f.read_text(encoding="utf-8"))
    mirror = s.root / ".agents" / "skills"
    for d in sorted(p for p in mirror.iterdir() if p.is_dir()) if mirror.exists() else []:
        if d.name not in expected:
            s.orphans.append(f".agents/skills/{d.name} has no source command or skill")


def run(root: Path, check: bool = False, prune: bool = False) -> Sync:
    s = Sync(root, check)
    s.write("AGENTS.md", compose_agents_md(root))
    sync_agents(s)
    sync_skills(s)
    if prune and not check:
        for orphan in s.orphans:
            target = root / orphan.split(" ", 1)[0]
            shutil.rmtree(target) if target.is_dir() else target.unlink()
    return s


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate the Codex mirror from the Claude config.")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--check", action="store_true", help="exit 1 if the mirror is out of date")
    ap.add_argument("--prune", action="store_true", help="delete mirror files with no source")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    s = run(Path(a.root), check=a.check, prune=a.prune)
    for orphan in s.orphans:
        print("orphan: " + orphan)
    if a.check:
        for rel in s.changes:
            print("out of date: " + rel)
        if not s.changes and not a.quiet:
            print("Codex mirror is up to date")
        return 1 if s.changes else 0
    if s.changes or not a.quiet:
        print(f"sync_codex: {len(s.changes)} file(s) written")
        for rel in s.changes:
            print("  wrote " + rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
