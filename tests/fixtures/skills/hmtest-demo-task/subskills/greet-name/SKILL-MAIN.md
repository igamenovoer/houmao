---
name: greet-name
description: Use when a demo request supplies a person's name or asks for the fixed greeting line and no other transform.
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

# Greet Name

## Overview

Produce exactly one greeting line for a supplied name. This is the smallest demo task in the fixture and has no external dependencies.

## When to Use

Use when the input is a single name or an explicit request for the demo greeting. Do not use when the input needs slugging or list formatting.

## Workflow

1. Trim leading and trailing whitespace from the supplied name.
2. If the trimmed name is empty or absent, use `World`.
3. Return exactly `Hello, <name>!` and nothing else.

## Output Contract

- The output is one line.
- The line matches `Hello, <name>!` with the trimmed name.
- No Markdown fences, quotes, or trailing notes.

## Guardrails

- DO NOT add a second sentence, explanation, or emoji.
- DO NOT change the `Hello, ` prefix or the `!` suffix.
- DO NOT read files or call tools for this task.
