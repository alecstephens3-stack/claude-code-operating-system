---
name: weekly-reset
description: Monday reset of the priorities file. Use when the owner says "weekly reset", "reset priorities", or when the context budget check reports the reset is overdue.
---

# Weekly reset

The priorities file loads into every session and wins over every other context file when they disagree. Left alone it grows by a note a day until it crowds out everything else, so it is reset every Monday.

1. Read `vault/priorities.md` in full, and re-read it right before writing: other sessions may have added lines.
2. Copy the whole file, unchanged, to `vault/archives/priorities/priorities-<last reset date>-to-<today>.md`. Never delete: archive.
3. Rewrite the live file with only what is live this week: open work, real deadlines, things waiting on someone. Finished items and old context go.
4. Update the `Last reset: YYYY-MM-DD` line in the header. `guards/check_context_budget.py` reads it.
5. Run `python3 guards/check_context_budget.py` and `python3 guards/lint_frontmatter.py`, and fix anything they report.
6. Tell the owner in one or two lines what moved out and what stays.
