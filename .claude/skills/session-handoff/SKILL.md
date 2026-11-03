---
name: session-handoff
description: Produce a structured end-of-session handoff in chat so a fresh session can continue without loss. Use when the owner says "session handoff", "hand off", "wrap up the session", or is about to clear the context. Covers decisions, what shipped, key files, running processes, how to verify, deferrals and open questions.
---

# Session handoff

The reader of this format is the next session, not the owner.

**Check who is reading first.** If the owner asked you to summarise the session for himself, this template is wrong: paths, process ids and commit hashes are noise to him. Gather with it if useful, then answer him in plain words per `.claude/rules/writing-style.md`, which outranks this file.

## How

1. Review the whole conversation, not the last few turns.
2. Pull state from: any plan file used this session, open tasks, background processes you started (their ids are the only way the next session can find them), files you created or changed, and questions that never got a clear answer.
3. Do not audit the repo. This is what happened in this session, and nothing else.
4. Output in chat only. Never write it to a file.

## Template (every section, every time; write "none" rather than dropping one)

```
# Session handoff: <one line on what this session was about>

## Where it started
<two or three sentences: the ask and the constraints that came up>

## Decided and shipped
- <decision or change>: <why, and where it lives>

## Key files for the next session
- `<absolute path>`: <why to read it first>

## Running state
- Background processes: <id, what it is, how to stop it> or none
- Servers and ports: <url> or none
- Branches and worktrees: <names> or none

## How to verify
- `<command>`: <expected result>

## Deferred and open
- Deferred: <item>: <why later>
- Open: <question for the owner>: <context>

## Pick up here
<one or two sentences: the single most likely next action>
```

## Rules

- Never invent state. Absolute paths always.
- If a plan file drove the session, name it first under key files.
- No retrospective and no praise. Terse and concrete, like an engineer's end-of-shift note.
