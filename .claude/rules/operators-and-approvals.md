# Operators and approvals

## One folder for the owner, one job per operator

The owner works from this folder and never changes directories. The main assistant here owns clients, delivery, finances, strategy and the vault. Two other operators live in their own repos, each with its own CLAUDE.md and memory:

- The outbound operator: lead sourcing, enrichment, openers, campaign drafts and reply triage.
- The media operator: video clips, captions and thumbnails.

Hand work to them with `/handoff <operator> <task>`. Never run their work inline here: their playbooks would crowd this context, and their rules would not load. Operators build drafts; the owner activates anything that goes out.

## What runs unattended

An operator started by another agent runs with a deny list on the hand-off channel (`operators/operators.json`): it can research, draft and build, but it cannot send, publish, push or delete. The deny list lives in configuration, not in the operator's prompt, because a prompt that says "don't" is a request and a permission is a wall.

## Sub-agents

Every agent in `.claude/agents/` declares a `tools:` allow-list in its front matter with the least it needs. Reviewers and verifiers are read-only. A reviewer that cannot edit cannot "fix" what it was asked to judge, and a verifier with no network cannot be talked into sending anything.

## Sending

Nothing goes to a client, a teammate or the public without the owner's explicit yes on that specific message. Drafts are free; sends are approved one at a time.

## Scheduled jobs

Scheduled jobs run on the machine's own cron through `jobs/run_job.py`. A job's output is its message: empty output sends nothing, so a message always means something needs attention. A crashed job always sends a message.
