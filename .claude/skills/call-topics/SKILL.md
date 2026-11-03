---
name: call-topics
description: Collect things the owner wants to raise on an upcoming call, across sessions, and pour them into that call's game plan. Use when the owner says "bring this up with X", "save this for the call with Y", "put that on the agenda for Tuesday", or anything that parks a topic for a future call. Also use when he asks to prep for a call, and after a call is processed, to clear what got covered.
argument-hint: "[who or which call] [the topic], or: game plan for [call]"
---

# Call topics

One running list per upcoming call, so a topic parked in Monday's session is still there on Thursday.

## Where the lists live

`vault/meetings/upcoming/<who>.md`, one file per person or recurring meeting, named by who and never by date (`office-manager.md`, `weekly-sync.md`). Create it the first time with this front matter:

```
---
type: meeting
title: "Topics for <who>"
summary: Running list of things to raise with <who>; feeds the next game plan
status: active
tags: [meeting, upcoming]
last-updated: <today>
---
# Topics for <who>

**Next call:** <date and time in both time zones, from the calendar, or "not booked">

## To raise
```

## Adding a topic

1. Pick the file from who the call is with. If two fit, pick the obvious one and say which in one line.
2. Append one bullet under **To raise**: `- (12 Oct) <the topic in the owner's words>`. Questions or detail he gave go in as sub-bullets.
3. Look up the next call on the calendar and refresh the **Next call** line.
4. Reply in one line: "Added to the office manager's list for Tue 13 Oct." No page, no checklist.

Never drop or rewrite earlier items when adding one.

## Building the game plan

When he asks to prep for the call:

1. Read the topics file in full, the project note and `vault/priorities.md`.
2. Build the game plan page on the design system, named `<who>-game-plan-<date>.html`. Every item under **To raise** goes in, marked with when it was added.
3. Open it and say in chat what it is and the first thing to read.

## After the call

When the recording is processed (the `meeting-notes` agent), move covered items to a `## Raised` section with the date and a few words on the outcome. Items not covered stay under **To raise**.
