"""End-to-end: the repo passes its own guards."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".md", ".py", ".json", ".txt", ".toml", ".cfg", ".ini", ".yml", ".yaml", ""}
SKIP = {".git", "__pycache__", ".pytest_cache", ".venv", "venv"}


def guard(*args):
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)


def repo_files():
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and not any(part in SKIP for part in p.relative_to(ROOT).parts):
            if p.suffix in TEXT_SUFFIXES:
                yield p


def test_no_em_or_en_dashes_anywhere():
    bad = [str(p.relative_to(ROOT)) for p in repo_files()
           if "\u2014" in p.read_text(encoding="utf-8") or "\u2013" in p.read_text(encoding="utf-8")]
    assert bad == []


def test_example_vault_is_clean():
    r = guard("guards/lint_frontmatter.py", "--today", "2026-10-17")
    assert r.returncode == 0, r.stdout


def test_home_page_is_current():
    r = guard("guards/build_home.py", "--check")
    assert r.returncode == 0, r.stdout


def test_codex_mirror_is_current():
    r = guard("guards/sync_codex.py", "--check")
    assert r.returncode == 0, r.stdout
    assert "orphan" not in r.stdout


@pytest.mark.parametrize("draft, profile, code", [
    ("examples/good-email.txt", "email", 0),
    ("examples/bad-email.txt", "email", 1),
    ("examples/proposal.txt", "proposal", 0),
])
def test_example_drafts(draft, profile, code):
    r = guard("guards/copy_check.py", draft, "--profile", profile)
    assert r.returncode == code, r.stdout


def test_budget_check_runs_on_the_repo():
    r = guard("guards/check_context_budget.py", "--today", "2026-10-17")
    assert r.returncode == 0
    assert "main instructions" in r.stdout
