---
name: handoff
description: Hand a task to another operator (outbound or media) in its own repo, without leaving this folder.
---
<!-- GENERATED from .claude/commands/handoff.md by guards/sync_codex.py -->

# /handoff

Hand `$ARGUMENTS` to the named operator. The first word is the operator, the rest is the task.

1. Write the brief so the operator can finish without coming back: the goal, the inputs and where they are, what done looks like, and the answers to any question you can predict it will ask.
2. Run `python3 operators/handoff.py <operator> "<brief>"`. Use `--continue` when you are answering a question the operator just asked, so it keeps its context.
3. Read the operator's reply. Relay what matters to the owner in plain words. If the operator needs a decision, ask the owner for the decision, never for a command to run.
4. Never relay a command for the owner to type. If something needs running, run it through the operator.

Operators draft. Anything that sends, publishes or deletes waits for the owner, and the hand-off channel's deny list makes that a permission, not a request.
