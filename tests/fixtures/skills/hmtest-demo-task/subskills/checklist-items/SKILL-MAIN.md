---
name: checklist-items
description: Use when a demo request supplies one or more short lines that must be rendered as a Markdown checkbox list.
metadata:
  skill_invocation_notation: >
    Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
    SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
    accepted only as legacy input when SKILL-MAIN.md is absent.
    Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
    `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
    `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
    subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
    by parent subcommand parent. Intermediate subcommands act as object generators.
    Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Checklist Items

## Overview

Render supplied lines as a Markdown task list without changing item text.

## When to Use

Use when the input is a newline-separated list of items and the expected output is checkboxes. Do not use for a single greeting or slug.

## Workflow

1. Split the input into lines.
2. Trim each line and drop blank lines.
3. If no items remain, return exactly `No items.`
4. Otherwise emit one `- [ ] <item>` line per item in the original order.

## Output Contract

- Each item appears exactly once and in input order.
- No extra heading, numbering, or explanation.
- The empty-input result is exactly `No items.`

## Guardrails

- DO NOT reorder, merge, or rewrite item text.
- DO NOT add checked boxes or extra Markdown sections.
- DO NOT emit blank checkbox lines for empty input lines.
