#!/usr/bin/env python3
"""run_job.py: run one scheduled job and report by message only when it matters.

The pattern: scheduled jobs run on the machine's own cron, not on a hosted
automation platform. Each job is a plain command. Its standard output IS the
message: empty output means everything is fine and nothing is sent, so the
owner's phone only buzzes when there is something to act on. A job that
crashes always sends a message, because a silent failure looks exactly like a
quiet week.

Every run leaves a trace in jobs/runs.log (time, job, exit code, whether a
message went out), so "did the Monday check run?" has an answer.

The message is delivered by NOTIFY_COMMAND, any command that reads the
message on stdin (a script that sends a text, a chat webhook, a mail command).
When it is not set, the message is printed instead.

    python3 jobs/run_job.py context-budget        # run one job now
    python3 jobs/run_job.py --list
    python3 jobs/run_job.py --crontab             # print crontab lines to install
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JOBS = Path(__file__).resolve().parent / "jobs.json"
DEFAULT_LOG = Path(__file__).resolve().parent / "runs.log"


def load(path: Path) -> dict:
    return {job["name"]: job for job in json.loads(path.read_text(encoding="utf-8"))["jobs"]}


def notify(message: str) -> None:
    cmd = os.environ.get("NOTIFY_COMMAND")
    if not cmd:
        print(message)
        return
    subprocess.run(shlex.split(cmd), input=message, text=True, check=True, timeout=60)


def run_job(job: dict, root: Path, log: Path) -> tuple[int, str]:
    """Run the job. Returns (exit code, the message sent, or "" when nothing was sent)."""
    try:
        proc = subprocess.run(job["command"], cwd=root, capture_output=True, text=True,
                              timeout=job.get("timeout_seconds", 600))
        code, out, err = proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        code, out, err = -1, "", str(exc)

    if code != 0:
        tail = "\n".join(err.splitlines()[-5:])
        message = "\n".join(part for part in (
            f"Scheduled job '{job['name']}' exited with code {code}.", out, tail) if part)
    else:
        message = out
    if message:
        notify(message)

    stamp = dt.datetime.now().isoformat(timespec="seconds")
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp}\t{job['name']}\texit={code}\tsent={'yes' if message else 'no'}\n")
    return code, message


def crontab(jobs: dict, root: Path) -> str:
    script = Path(__file__).resolve()
    return "\n".join(f"{job['schedule']} cd {shlex.quote(str(root))} && "
                     f"{shlex.quote(sys.executable)} {shlex.quote(str(script))} {shlex.quote(name)}"
                     for name, job in sorted(jobs.items()))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a scheduled job; message only when it has something to say.")
    ap.add_argument("name", nargs="?")
    ap.add_argument("--jobs", default=str(DEFAULT_JOBS))
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--log", default=str(DEFAULT_LOG))
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--crontab", action="store_true")
    a = ap.parse_args(argv)

    jobs = load(Path(a.jobs))
    if a.crontab:
        print(crontab(jobs, Path(a.root)))
        return 0
    if a.list or not a.name:
        for name, job in sorted(jobs.items()):
            print(f"{name:20} {job['schedule']:15} {job.get('about', '')}")
        return 0
    if a.name not in jobs:
        print(f"unknown job {a.name!r}. Known: {', '.join(sorted(jobs))}")
        return 2
    code, _ = run_job(jobs[a.name], Path(a.root), Path(a.log))
    return 0 if code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
