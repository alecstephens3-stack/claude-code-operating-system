# Vault front matter

Every note in `vault/` opens with a front matter block. The generated home page, table views in a markdown editor, and the assistant itself all read these fields, so a note without them is invisible to all three.

The machine-readable source of truth is `guards/vault_schema.json`. This page explains the fields; it does not restate the lists, because a copied list drifts. Read the JSON for the current allowed types, statuses and per-type fields.

## Universal fields

```yaml
---
type: project
title: Example Co. order intake
summary: One line shown next to the link on the home page, no trailing period
status: active
tags: [project, client/example-co]
last-updated: 2026-10-12
---
```

- `type`: exactly one value from the schema. Drives which section and which extra fields apply.
- `title`: what shows in tables and links.
- `summary`: the most important field. It is what makes the vault scannable. A sentence fragment, no period.
- `status`: where the note is in its life. `active` notes that go untouched for too long get a STALE warning.
- `tags`: a list. Include the type as a tag.
- `last-updated`: an ISO date, changed when the content meaningfully changes.

## Per-type fields

Some types need more. A `project` names its `client`; a `research` note carries the `date` and `topic`; a `decision` carries the `date` and the `area` it affects. The schema's `types` table is the full list.

## The subset of YAML that works here

Notes use `key: value`, `key: [a, b]` and quoted strings, nothing else. A value with a colon in it must be quoted:

```yaml
title: "Call notes: pricing"
```

Unquoted, full YAML reads that as a nested key and the note drops off the home page. The linter reports it as UNPARSEABLE instead of guessing.

## Checking

```
python3 guards/lint_frontmatter.py     # errors fail, warnings do not
python3 guards/build_home.py --check   # is HOME.md current?
```
