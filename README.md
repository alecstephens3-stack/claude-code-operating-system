# Claude Code Operating System

The machinery behind an AI operating system that a small AI consultancy runs its day-to-day work on, built on Claude Code. One main assistant handles clients, delivery, finances and strategy from a markdown vault. Separate operator projects handle outbound sales and media. Scheduled jobs watch the system and send a message only when something needs attention. Guard scripts check the things a model gets wrong when nobody is looking.

This repo is a clean, generic extract of the private setup: the structure, the agents, the rules and the guards, with a tiny fictional vault (a made-up client, Example Co.) to run them against. It contains no client data.

## The problem

Running a business through an AI assistant works well for a week. Then the failures start, and none of them throws an error:

- **Context fills up without warning.** The instructions and memory that load every session grow until the loader cuts the tail, and the tail holds the oldest, hardest-won rules.
- **Drafts carry claims nobody checked.** A confident email cites a number nobody measured, or names a tool the business stopped using months ago.
- **Agents do more than they were asked.** A reviewer with write access "fixes" the thing it was asked to judge. A third-party skill can carry instructions that take over the assistant's tools.
- **One context tries to hold every job.** Outbound sales playbooks and video production notes crowd out the rules that matter for client work.
- **Two coding agents read two copies of the instructions.** The project is opened in both Claude Code and Codex, and hand-kept copies disagree within a week.
- **Scheduled reports become noise.** A job that messages every day trains everyone to ignore the day it matters.

Each of these was learned in production. Each answer here is a structure or a tested script, not a sentence asking the model to be more careful.

## How it fits together

```
                               Owner
                       (one folder, one chat)
                                 |
                                 v
  +--------------------------------------------------------------+
  |  Main assistant ("Charlie"), this repo                       |
  |  clients, delivery, finances, strategy, the vault            |
  |                                                              |
  |  sub-agents, each with a tool allow-list in front matter:    |
  |    adversarial-reviewer      read-only, plus web lookups     |
  |    skill-security-verifier   read-only, no network           |
  |    plain-reader              read-only                       |
  |    research-agent            web, writes reports only        |
  +--------------------------------------------------------------+
          |                       |                       |
   /handoff outbound       /handoff media        guards/sync_codex.py
          |                       |                       |
          v                       v                       v
  +-----------------+    +-----------------+    AGENTS.md, .codex/, .agents/
  | outbound        |    | media           |    (one-way mirror for Codex)
  | operator        |    | operator        |
  | own repo,       |    | own repo,       |
  | own CLAUDE.md,  |    | own CLAUDE.md,  |
  | own memory      |    | own memory      |
  +-----------------+    +-----------------+
   Operators draft. Sending, publishing, pushing and deleting are
   denied on the hand-off channel, so the owner activates anything
   that goes out.

  Markdown vault (vault/)
    every note carries canonical front matter
    lint_frontmatter.py checks it, build_home.py generates HOME.md

  Local cron --> jobs/run_job.py --> a guard's output --> a phone message
                                     empty output = no message
                                     a crash always sends one
```

## What is in the repo

```
CLAUDE.md                      main assistant instructions (short on purpose)
.claude/
  settings.json                permission denies + hooks (budget check, mirror sync)
  agents/<name>/agent.md       four sub-agents with least-privilege tool lists
  rules/                       writing style, working principles, operators and approvals
  commands/handoff.md          the /handoff slash command
  skills/weekly-reset/         the Monday priorities reset
AGENTS.md, .codex/, .agents/   generated Codex mirror (never edited by hand)
guards/
  copy_check.py                lints outgoing drafts       (rules in copy_rules.json)
  check_context_budget.py      measures always-loaded files (budgets in budget.json)
  lint_frontmatter.py          checks vault front matter    (schema in vault_schema.json)
  build_home.py                generates the vault home page
  sync_codex.py                regenerates the Codex mirror
  frontmatter.py               small dependency-free front matter reader
operators/
  handoff.py, operators.json   runs a task headless in another operator's repo
jobs/
  run_job.py, jobs.json        scheduled jobs that report only when it matters
vault/                         fictional example vault (Example Co.)
examples/                      drafts to run the copy linter against
docs/
  vault-schema.md              what the front matter fields mean
  decay-ledger.md              how often each layer gets reviewed
tests/                         pytest suite, offline
```

## Design principles

**Guards over guidance.** When a written rule fails once, writing a longer rule rarely fixes it. The fix is a check in the build that fails loudly, tested against the real failure. Banned words, banned punctuation, unproven numbers, malformed front matter and a drifting mirror are all caught by scripts here, not by hoping the model remembers.

**Restrict with permissions, never with a prompt that says "don't".** A prompt is a request; a permission is a wall. If an agent could do something, assume it eventually will. So every sub-agent declares a tool allow-list in its front matter, and the reviewers and the security verifier get no write or shell tools at all: a reviewer that cannot edit cannot "fix" what it was asked to judge, and a verifier with no network cannot be talked into sending a file anywhere, whatever the file under review tells it. The same idea runs through the rest of the system. Operators started by the main assistant run with a deny list on the hand-off channel. The project settings deny reading `.env` files and force pushes. The Codex mirror carries it across too: an agent with no write tools gets a read-only sandbox there. A test (`tests/test_agents.py`) fails the build if an agent drops its allow-list or a reviewer gains a write tool.

**One source of truth, everything else generated.** A copy drifts. `CLAUDE.md` and `.claude/` are the only hand-edited instructions; the Codex side is regenerated from them. The home page is generated from front matter. The lint reads its schema from one JSON file, and the docs explain the schema without restating it. The copy linter reads its banned phrases from one config, so the rule and the check cannot disagree.

**Separate operators, one folder for the owner.** Each large job (outbound, media) gets its own repo, instructions and memory, so its playbook never crowds the main context. The owner never changes directories: `/handoff` runs the operator headless in its own repo and relays the answer, and `--continue` picks up the same conversation when the operator has a question.

**Silent unless it matters.** A scheduled job's output is its message. No output, no message. A crash always sends one, because a silent failure looks exactly like a quiet week. Every run still leaves a line in a log.

**Plain code for known answers, the model for judgment.** Known steps with known answers go to scripts, cron and spreadsheets. The model reads messy input and makes the calls a script cannot. "This does not need AI" is a valid recommendation.

**Draft, don't send.** Nothing goes to a client or the public without the owner's yes on that specific message. Oversight matches consequence: internal drafts just run, anything that sends, spends, deploys or changes shared data waits for approval.

**Every layer has a review clock.** Priorities go stale in a week, rules in months, and instructions written for one model become dead weight when the next model no longer needs them. `docs/decay-ledger.md` gives each layer its own clock, including a model-fit pass on every switch of the default model.

The working principles are grouped under the acronym VAULT (Verify, Augment, Understand, Loop humans in, Transparency); the acronym comes from a public video by Nate Herk. The full text is in `.claude/rules/working-principles.md`.

## The guards

| Script | What it stops | How |
|---|---|---|
| `copy_check.py` | Drafts with banned phrases, em or en dashes, retired tools, or numbers nobody measured | FAIL for rules with one right answer; VERIFY for any number with a unit that is not in a proof file. Profiles for emails, proposals and HTML pages |
| `check_context_budget.py` | Always-loaded files growing past the point where the loader cuts them | Measures each layer against its limit. Silent below the warning line; a short block at session start or a phone message above it |
| `lint_frontmatter.py` | Notes that drop off the home page or point at notes that do not exist | Required fields, allowed types and statuses, ISO dates, list tags, broken wikilinks, stale active notes |
| `build_home.py` | A hand-kept index that drifts | Rebuilds the blocks between AUTO markers from front matter; `--check` fails if the page is out of date |
| `sync_codex.py` | Two coding agents reading two different sets of instructions | Regenerates `AGENTS.md`, Codex agent files and skills from the Claude side; `--check` fails on drift; carries read-only agents across as a read-only sandbox |

Try them:

```
python3 guards/copy_check.py examples/bad-email.txt --profile email
python3 guards/copy_check.py examples/proposal.txt --profile proposal
python3 guards/check_context_budget.py
python3 guards/lint_frontmatter.py
python3 guards/build_home.py --check
python3 guards/sync_codex.py --check
python3 jobs/run_job.py --crontab
python3 operators/handoff.py outbound --dry-run "draft three openers for the new list"
```

## Running the tests

The scripts use only the Python standard library (3.11 or newer). The tests need pytest and run offline.

```
python3 -m pip install pytest
python3 -m pytest
```

The suite unit-tests every guard and the job and hand-off runners, then runs the repo against its own guards end to end: no em or en dashes anywhere, a clean example vault, a current home page, a current Codex mirror, and the example drafts passing or failing as they should.

## License

MIT. See `LICENSE`.
