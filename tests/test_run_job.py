import sys

import pytest

import run_job as rj


@pytest.fixture
def outbox(tmp_path, monkeypatch):
    box = tmp_path / "outbox.txt"
    sender = tmp_path / "send.py"
    sender.write_text(f"import sys\nopen({str(box)!r}, 'a').write(sys.stdin.read() + '\\n--\\n')\n")
    monkeypatch.setenv("NOTIFY_COMMAND", f"{sys.executable} {sender}")
    return box


def job(code):
    return {"name": "t", "schedule": "0 9 * * 1", "command": [sys.executable, "-c", code]}


def test_empty_output_sends_nothing_but_logs(tmp_path, outbox):
    log = tmp_path / "runs.log"
    assert rj.run_job(job("pass"), tmp_path, log) == (0, "")
    assert not outbox.exists()
    assert "\tt\texit=0\tsent=no" in log.read_text()


def test_output_is_the_message(tmp_path, outbox):
    code, msg = rj.run_job(job("print('Something needs you.')"), tmp_path, tmp_path / "runs.log")
    assert code == 0 and msg == "Something needs you."
    assert "Something needs you." in outbox.read_text()


def test_failure_always_sends(tmp_path, outbox):
    code, msg = rj.run_job(job("import sys; sys.stderr.write('boom'); sys.exit(3)"),
                           tmp_path, tmp_path / "runs.log")
    assert code == 3
    assert "exited with code 3" in msg and "boom" in msg
    assert "sent=yes" in (tmp_path / "runs.log").read_text()


def test_missing_command_is_a_failure_not_a_crash(tmp_path, outbox):
    bad = {"name": "t", "schedule": "* * * * *", "command": ["/no/such/binary"]}
    code, msg = rj.run_job(bad, tmp_path, tmp_path / "runs.log")
    assert code == -1 and "exited with code -1" in msg


def test_crontab_lines_cover_every_job(tmp_path):
    jobs = rj.load(rj.DEFAULT_JOBS)
    lines = rj.crontab(jobs, tmp_path).splitlines()
    assert len(lines) == len(jobs)
    assert all(line.split()[5] == "cd" for line in lines)


def test_unknown_job(capsys):
    assert rj.main(["nope"]) == 2
    assert "unknown job" in capsys.readouterr().out
