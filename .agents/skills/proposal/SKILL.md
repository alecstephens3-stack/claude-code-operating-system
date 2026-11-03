---
name: proposal
description: Write a freelance marketplace proposal and an answer to every screening question from a pasted job post. Use when the owner pastes a job post or says "apply to this" or "write a proposal". Starts with a fit read; proof comes from vault/proof.md and the draft is checked before it is handed over.
argument-hint: "[job post]"
---

# Proposal

The owner reviews and submits it himself. Nothing here submits anything.

## Facts about the platform that change the writing

- A ranking model reads the proposal before a person does, scoring the text and the screening answers against the job. Use the post's own words for its requirements. A proposal that would fit another job scores low with the model and with the person.
- Speed matters more than polish on a new post. Write the first draft in one pass; skip the reviewer only if the owner says it is a race.
- Pricing goes in the bid box, never the text. Contact details and booking links before a contract break the platform's rules, and `copy_check.py` fails them.

## Steps

1. **Fit read, in chat only.** Three lines: can he cover the hours the job needs, what the post shows about the client (payment verified, hire rate, spend), and a verdict (apply, apply now, skip) with one reason.
2. **Pick the type:** `cold` (100 to 150 words) by default, `detailed` (200 to 300) when the post lists what to include, `invited` (150 to 200) when the client invited him. The ranges live in `guards/copy_rules.json`.
3. **Acceptance criteria first:** the type, the one proof point and the file it came from, the two details from the post the hook will name, every screening question, and the yes-or-no question you will close on. If you cannot fill this in, read the post again.
4. **Draft** the cover letter and each screening answer.
5. **Check:**

   ```
   python3 guards/copy_check.py cover.txt --profile proposal --type cold
   python3 guards/copy_check.py answer1.txt --profile proposal --type screening
   ```

   Fix every FAIL and re-run. A VERIFY number gets a source in `vault/proof.md` or is cut.
6. **Second opinion:** hand the clean draft to `adversarial-reviewer`, or `owner-reviewer` if the buyer runs a clinic. Act on anything it raises twice.
7. **Hand over:** the fit read, the cover letter in a code block, each screening answer in its own block under its question, the work sample to attach, and one line on what was checked.

## Shape

1. **Hook:** two specific details from their post, in their words.
2. **Proof:** one real build and one number from `vault/proof.md`, told the way you would mention it to a colleague. Match the proof to what the job is judged on, not to the flagship project.
3. **Approach:** if they listed deliverables, bullets that map to their list with what "done" looks like; if they described a problem, a short paragraph on what you would learn first, build, and hand over.
4. **Close:** a yes-or-no question.

Never open with "I" or a greeting. No generic enthusiasm. Name a tool only if it answers something they asked. If the post asks for a tool we do not use, do not claim it: say we build on what they already pay for.

## Proof is read, never restated

There is no list of proof points in this file on purpose. A hard-coded list goes stale the month the business changes and then blocks the real work from every proposal. Read `vault/proof.md` each time.
