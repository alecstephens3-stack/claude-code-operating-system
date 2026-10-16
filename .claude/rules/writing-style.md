# Writing style

These apply to everything the assistant writes. The mechanical ones are also enforced by `guards/copy_check.py`, which reads its word lists from `guards/copy_rules.json`. When this file and that config disagree, the config is what runs, so change both together.

## Plain words

- Lead with the answer or the action, not the reasoning.
- Short sentences, everyday words, no throat-clearing openers ("Quick one", "I wanted to reach out").
- No corporate filler ("circle back", "touch base", "move the needle", "synergy") and no empty superlatives ("world-class", "cutting-edge").
- No figurative "eats time" or "eat the cost". Say what it costs: "takes an hour a day".
- Lists only when there are three or more parallel items. Quick questions get quick answers.

## No em dashes

Never use an em dash or an en dash in anything that goes out: emails, proposals, posts, pages, docs. Use a period, a comma or a colon. The copy linter fails any draft that contains one.

## Explain for the owner, not the system

The owner reads the chat, not the code.

- Say what something means for him or the client before saying what it is. "The new hires' sheets now land in the right folder" beats "repointed the folder id".
- Do not name functions, config keys, tabs or file paths unless he has to click on or type that thing.
- Separate what is true from how it was checked. The what goes in the chat. The how goes in the vault, with one line in the chat saying where.
- Plain and adult, not simplified. Cut jargon, not substance.

This outranks any skill's output template. A skill decides how to gather; it does not decide who is reading.

## Client emails

- Short: what changed, what they need to do, then stop. The cause gets one sentence, not a section.
- Warm and calm. About one exclamation point per email, saved for the close or a real win.
- Before asking a client for anything, check three things: can we get it ourselves from a system we already reach, can someone else answer it, and is it a preference (worth asking) or a fact (usually not). Default to one ask per email, and some emails should ask for nothing.
- When something broke on our side, say so plainly and take it off their plate.

## Numbers

A number in outgoing copy must come from a proof file (`vault/proof.md` in the example vault). The copy linter flags any number with a unit that does not appear in one. A teammate's figure, an agent's report or an earlier reading is an input, not a fact, until it is checked against the source in the same turn.
