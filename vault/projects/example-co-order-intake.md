---
type: project
title: Example Co. order intake
summary: Web form orders land in the shop's existing spreadsheet, a person approves each one
status: active
client: Example Co.
tags: [project, client/example-co]
last-updated: 2026-10-12
---

# Example Co. order intake

**The problem:** the shop manager retyped every web order into the stock spreadsheet by hand, and typos turned into wrong shipments.

**A good result:** orders arrive in the spreadsheet already filled in, and the manager only checks and approves.

## How it works

- Trigger: a new order email from the shop's existing web form.
- Steps: a small script reads the email, fills a row, and marks it "to check". Known fields are copied as they are; the model only reads the free-text notes.
- Human approval: nothing moves to "ready to ship" until the manager ticks it.
- Why not a new tool: the shop already pays for the spreadsheet and the form, see [[2026-10-02-build-on-existing-spreadsheet]].

Research: [[2026-10-01-order-form-options]].
