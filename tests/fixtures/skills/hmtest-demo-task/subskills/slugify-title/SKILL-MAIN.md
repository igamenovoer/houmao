---
name: slugify-title
description: Use when a demo request supplies a title that must be converted to a lowercase hyphenated URL slug.
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

# Slugify Title

## Overview

Convert one title string into a deterministic URL slug.

## When to Use

Use when the input is a title and the expected output is a slug. Do not use for greeting or list formatting.

## Workflow

1. Trim the title and convert it to lowercase.
2. Replace every run of characters outside `a-z0-9` with a single hyphen.
3. Remove leading and trailing hyphens.
4. If the result is empty, return `untitled`; otherwise return the slug.

## Output Contract

- The output is one line containing lowercase letters, digits, and single hyphens.
- The slug has no leading or trailing hyphen.
- No Markdown fences or explanation.

## Guardrails

- DO NOT preserve uppercase letters, spaces, or punctuation.
- DO NOT collapse separate words into one token without a hyphen.
- DO NOT return an empty line.
