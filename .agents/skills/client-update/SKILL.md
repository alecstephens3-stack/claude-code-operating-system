---
name: client-update
description: Write a short project status update for a client, checked before the owner sees it. Use for "update for <client>", "status update", "let <client> know where we are", or an end-of-milestone note, by email or chat.
argument-hint: "[client or project]"
---

# Client update

A status update the client can act on. Short, warm, concrete.

## Before writing

1. Read the project note in `vault/projects/` and `vault/priorities.md`. They are the current state and they beat your memory of the session.
2. Check that anything you are about to call done is done: the commit, the deploy, the email in the sent folder. Other sessions write to the same files, so re-read them in this turn.
3. Ask the owner for what the vault cannot know: a demo that happened, a blocker, something needed from the client.

## What it says

Three things, in this order, and nothing else:

1. **What changed**, in the client's words, led by what it means for them: "new orders land in your sheet already filled in," never "the intake webhook was repointed."
2. **What they need to do**, if anything, and by when. One ask. Before adding it, check whether we could get the answer ourselves or from someone else. Some updates ask for nothing.
3. **What is next from us**, in a sentence.

Wins before blockers. A cause gets one sentence, never a section. Anything they do not need in order to act goes in the vault.

## Gate (not optional)

1. Write the acceptance criteria first: who it goes to, the one change they care about, the single ask or "no ask", the channel.
2. Draft into a scratch file and run:

   ```
   python3 guards/copy_check.py <draft> --profile email
   ```

   FAIL lines are fixed, every time. A VERIFY number gets a source in `vault/proof.md` or gets cut. Over 100 words needs `--long "reason"`, and the reason has to hold for every paragraph.
3. Show the owner the text in the chat, ready to paste, with one line on what was checked. Never create a draft in the mail client unless he asked, and never send.
