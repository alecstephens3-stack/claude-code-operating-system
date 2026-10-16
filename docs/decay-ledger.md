# The decay ledger

Every layer of an AI operating system goes stale, and each at its own speed. Priorities are out of date within a week. Rules drift over months as habits change. Instructions written for one model become dead weight when a stronger model no longer needs them spelled out. Nothing announces any of this; the system just gets a little worse.

So each layer gets its own review clock, and the ledger records when it was last actually reviewed, which is not the same as when it was last edited.

| Layer | Clock | What it covers |
|---|---|---|
| Priorities | weekly | `vault/priorities.md`, via the `weekly-reset` skill |
| Context budget | weekly, automated | everything that loads every session (`guards/check_context_budget.py`) |
| Vault health | weekly, automated | front matter, broken links, stale active notes (`guards/lint_frontmatter.py`) |
| Rules | monthly | `.claude/rules/` |
| Agents and skills | monthly | `.claude/agents/`, `.claude/skills/`: is each one still used, and is each tool on its allow-list still needed? |
| Scheduled jobs | monthly | `jobs/jobs.json`: does every job still produce a message worth reading? |
| Hooks | twice a year | `.claude/settings.json` |
| Model fit | on every switch of the default model | every always-loaded instruction, asked one question: does the current model still need this? |

## How to read a review

- An agent or skill that never fired in the review window goes on a shortlist, not a kill list. Ask why: a wrong trigger description, a seasonal job, or a model that has outgrown it.
- Counts come from a script, never from this table. A number typed into a ledger is wrong within days.
- Archiving is the owner's call. The review reports; it does not delete.

## The model-fit pass

When the default model changes, read every always-loaded instruction and split it into two piles:

- **Keep:** facts the model cannot know (names, prices, banned words, client-specific gotchas, hard-won rules).
- **Cut:** procedures the model now works out alone. Move them to an archive folder, verbatim, so they can come back if the cut was wrong.

Shorter instructions load faster, cost less, and leave room for the rules that matter.
