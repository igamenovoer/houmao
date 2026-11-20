---
name: title-case
description: Use when a demo request supplies a short title or phrase that must be converted to the fixed Title Case form.
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

# Title Case

## Overview

Convert one short title or phrase into a deterministic Title Case line.

## When to Use

Use when the input is a title or phrase and the expected output is Title Case. Do not use for greetings, slugs, or list formatting.

## Workflow

1. Trim the input and collapse every whitespace run to one space.
2. If the result is empty, return `Untitled`.
3. Split the result into words.
4. Uppercase the first character of each word and lowercase the remaining characters.
5. Join the words with single spaces and return the line.

## Output Contract

- The output is one line with single spaces between words.
- Each word starts with an uppercase character and has no other uppercase characters.
- Input punctuation stays in place; no punctuation is added or removed.
- No Markdown fences or explanation.

## Guardrails

- DO NOT reorder, merge, or drop words.
- DO NOT change punctuation or add a trailing period.
- DO NOT return an empty line.
