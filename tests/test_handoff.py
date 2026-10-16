import pytest

import handoff as ho

CONFIG = {
    "always_deny": ["mcp__mail__send"],
    "operators": {"outbound": {"repo": "~/dev/outbound-operator", "deny": ["Bash(*launch*)"]}},
}


def test_command_runs_headless_with_both_deny_lists():
    cmd = ho.build_command(CONFIG, "outbound", "draft openers")
    assert cmd[:3] == ["claude", "-p", "draft openers"]
    assert cmd[cmd.index("--disallowedTools") + 1] == "mcp__mail__send,Bash(*launch*)"
    assert "-r" not in cmd


def test_continue_picks_up_the_last_session():
    cmd = ho.build_command(CONFIG, "outbound", "answer", prior_session="abc123")
    assert cmd[cmd.index("-r") + 1] == "abc123"


def test_unknown_operator_is_refused():
    with pytest.raises(SystemExit, match="unknown operator"):
        ho.build_command(CONFIG, "finance", "x")


def test_repo_path_expands_home():
    assert "~" not in str(ho.operator(CONFIG, "outbound")["repo"])


def test_dry_run_prints_the_command(capsys):
    assert ho.main(["outbound", "draft openers", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("cd ") and "--disallowedTools" in out


def test_continue_without_history_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(ho, "SESSION_DIR", tmp_path)
    with pytest.raises(SystemExit, match="no earlier hand-off"):
        ho.main(["outbound", "--continue", "answer"])


def test_shipped_config_denies_sending_for_every_operator():
    config = ho.load(ho.DEFAULT_CONFIG)
    for name in config["operators"]:
        joined = ",".join(ho.build_command(config, name, "x"))
        assert "send_message" in joined and "git push" in joined
