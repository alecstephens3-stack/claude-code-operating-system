# Claude Code Operating System

I run a small AI consultancy, and most of the day-to-day work goes through Claude Code: client notes, delivery, the books, drafts of everything that gets sent. This repo is the machinery from that setup with the business taken out. It has the agents and their permissions, the rules, the guard scripts with their tests, and a tiny fictional vault (Example Co., Northside Dental) to run them against. There is no client data in it.

Most of what's here exists because something went wrong once. A memory file grew past the loader's line limit and the oldest rules stopped loading for nine days. A draft went out with a link that had a full stop glued to the end. A session claimed it had used the design system and had not opened a single file from it. Each time the fix was a script that fails loudly, plus a test that replays the original failure. Longer instructions did not hold.

## How it fits together

```mermaid
flowchart TD
    owner([Owner, one folder, one chat])
    main[Main assistant<br/>clients, delivery, books, the vault]
    owner --> main

    subgraph agents[Sub-agents, allow-lists in front matter]
        rev[adversarial-reviewer<br/>owner-reviewer<br/>plain-reader]
        sec[skill-security-verifier<br/>Read, Grep, Glob only]
        res[research-agent]
        mtg[meeting-notes<br/>4 named recorder tools]
        led[ledger-reader<br/>Bash behind a command hook]
    end
    main --> agents

    main -- /handoff --> outbound[Outbound operator<br/>own repo, own memory]
    main -- /handoff --> media[Media operator<br/>own repo, own memory]

    main --> vault[(Markdown vault<br/>front matter, generated HOME.md)]
    main -. sync_codex.py .-> codex[AGENTS.md, .codex/, .agents/<br/>one-way mirror for Codex]

    subgraph hooks[Hooks]
        h1[SessionStart: context budget]
        h2[PostToolUse: design system check, mirror sync]
        h3[PreToolUse: per-agent command guard]
        h4[git pre-commit: secret scan]
    end
    main --- hooks

    cron[Local cron] --> runjob[jobs/run_job.py] --> phone([Message to the owner<br/>only when output is non-empty])
```

Operators draft. Sending, publishing, pushing and deleting are denied on the hand-off channel, so the owner is the one who activates anything that goes out.

## Principles

I group the working rules under VAULT, an acronym I took from a public video by Nate Herk. The full text is in `.claude/rules/working-principles.md`.

- Verify the output. A tidy answer is a draft until the parts that matter are checked, and a clean log only proves the thing ran.
- Augment, don't replace. Known steps go to plain code; the model gets the messy input and the judgment calls.
- Understand the why. One line before any build: the problem, and what a good result looks like.
- Loop humans in. Drafts run freely. Anything that sends, spends, deploys or changes shared data waits for a yes.
- Transparency. Every automation says what triggers it, what it reads, and where a person approves.

The one I lean on most: restrict an agent with permissions, never with a prompt that says "don't". If an agent could do something, I assume it eventually will.

## Agents

Each agent lives in `.claude/agents/<name>/agent.md` with its tool list in front matter. `tests/test_agents.py` fails the build if an agent drops its list, a reviewer gains a write tool, an MCP grant covers a whole server, or an agent with Bash is missing its command guard.

| Agent | Tools | Why that list |
|---|---|---|
| adversarial-reviewer | Read, Grep, Glob, WebSearch, WebFetch | A reviewer that can edit will "fix" what it was asked to judge |
| owner-reviewer | Read, Grep, Glob, WebSearch, WebFetch | Same, reading as a clinic owner |
| plain-reader | Read, Grep, Glob | Reads a finished build as the person who has to use it |
| skill-security-verifier | Read, Grep, Glob | Vets third-party skills; with no network it can't be talked into sending anything |
| research-agent | Read, Grep, Glob, WebSearch, WebFetch, Write | Writes its report to the vault, has no shell |
| meeting-notes | Read, Write, Edit, Grep, Glob, four recorder tools | Named tools only, no shell |
| ledger-reader | Bash | A PreToolUse hook allows three read commands of `tools/ledger.py` and blocks pipes, redirects and chaining |

Front matter can grant Bash or withhold it, with nothing in between. The ledger-reader is how I got the in-between: Bash plus `guards/guard_agent_bash.py` wired as a hook in the agent's own file. Codex can't run Claude hooks, so `sync_codex.py` gives that agent a read-only sandbox on the Codex side instead.

Skills in `.claude/skills/`: `weekly-reset`, `call-topics`, `client-update`, `proposal`, `session-handoff`. The last one checks who is reading before it uses its template. I added that line after it handed me a wall of shell ids when I'd asked for a summary for myself.

## Guards

Everything below runs on the standard library. The failure column is what happened before the guard existed.

| Script | The failure it was written after |
|---|---|
| `guards/copy_check.py` | Drafts going out with banned phrases, em dashes, a number nobody measured, a link with trailing punctuation, or a 148-word reply to a two-line question. It also fails contact details in marketplace proposals, and `--profile` is required because a missing flag once ran a video description through the proposal rules |
| `guards/check_context_budget.py` | The memory index passed its line limit and the tail stopped loading. It now also flags memory files no index links to, priorities bullets that have turned into diaries, and an overdue decay ledger review |
| `guards/priorities_trim_check.py` | A weekly trim dropped four open items along with the history. It lists ticket ids, file pointers, emails, amounts and links that only the archive copy still has |
| `guards/check_design_system.py` | A page claimed the design system and carried none of it, then a private page opted itself out with a reason it wrote for itself. Opt-outs now have to name a category from a fixed list |
| `guards/guard_agent_bash.py` | Nothing yet, and I want to keep it that way: an agent that reads the books could otherwise copy them anywhere its shell reaches |
| `guards/guard_secret_commit.py` | Covers the paths `.env` deny rules don't: a key pasted into a note, a balance printed into a log. On its first run it blocked my own commit, because its docstring held a sample account line |
| `guards/lint_frontmatter.py`, `build_home.py` | Notes falling off the home page, and a hand-kept index drifting |
| `guards/sync_codex.py` | Claude Code and Codex reading two copies of the instructions that disagreed within a week |

Two small tools sit in `tools/`. `add_key.py` takes a secret through a macOS password dialog and writes it to `.env`, so the value never passes through the chat. `open_checklist.py` turns steps I have to do by hand into a page with tick boxes and Copy buttons, because a numbered list in the chat scrolls away while I'm clicking through a console.

Scheduled jobs go through `jobs/run_job.py`. A job's stdout is the message: empty output sends nothing, and a crash always sends one.

## Running it

Python 3.11 or newer. The tests need pytest and run offline.

```
python3 -m pip install pytest
python3 -m pytest
python3 guards/guard_secret_commit.py --install   # git doesn't version hooks
```

Some things to try:

```
python3 guards/copy_check.py examples/bad-email.txt --profile email --offline
python3 guards/copy_check.py examples/proposal.txt --profile proposal --type cold
python3 guards/check_context_budget.py
python3 guards/sync_codex.py --check
python3 tools/ledger.py find northside
echo '{"tool_input":{"command":"python3 tools/ledger.py summary > out.txt"}}' | python3 guards/guard_agent_bash.py ledger-reader
```

The suite also runs the repo against its own guards: no em dashes anywhere, a clean example vault, a current home page and a current Codex mirror.

## Limitations

- The guards are pattern matchers. `copy_check.py` can tell you a number isn't in the proof file; it can't tell you the claim is persuasive or that the right proof was picked. That still needs a reviewer agent and then me.
- `add_key.py` is macOS only.
- `guard_agent_bash.py` matches whole command strings. It's strict on purpose, which means every new read command needs a new pattern in `agent_commands.json`.
- The design system guard only judges new files. Pages already committed are left alone, otherwise every edit to an old page would turn into a migration and the guard would get switched off.
- The operators' own repos (outbound and media) aren't here, only the hand-off side.
- How Charlie writes in chat lives in a separate mod, [claude-code-voice-mod](https://github.com/alecstephens3-stack/claude-code-voice-mod).

## License

MIT. See `LICENSE`.
