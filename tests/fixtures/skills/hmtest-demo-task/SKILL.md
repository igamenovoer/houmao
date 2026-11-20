---
name: hmtest-demo-task
description: Use when a test needs a small parent skill that installs four self-contained demo tasks, or when verifying skill discovery, subskill routing, or fixture updates.
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

# Hmtest Demo Task

## Overview

Fixture skill for Houmao skill installation and update tests. It routes to four self-contained subskills that need no external tools, network, or credentials, so each installed revision has an exact expected output.

## When to Use

Use this skill when a test must verify skill installation, discovery, parent-to-subskill routing, or update replacement with a small isolated fixture. Use it when the request names one of the four demo tasks. Do not use it for production work or when the task needs inputs beyond a short text snippet.

## Workflow

When this skill is invoked, execute the following steps in order.

1. **Select one subskill** from **Subskills**. If the request does not name or clearly match one route, ask which demo task to run.
2. **Load exactly one child entrypoint** at the listed path. Do not preload sibling subskills.
3. **Run the child workflow** with the user's input and keep the child's output contract exact.
4. **Return the child output** without adding commentary unless the user asks for an explanation.

If the request spans multiple demo tasks, run them one at a time and label each result with its route name.

## Subskills

| Route | Entrypoint | When to Route Here |
| --- | --- | --- |
| `greet-name` | `subskills/greet-name/SKILL-MAIN.md` | The request provides a name, or deliberately omits one, and expects the fixed one-line greeting. |
| `slugify-title` | `subskills/slugify-title/SKILL-MAIN.md` | The request provides a title that must become a lowercase hyphenated URL slug. |
| `checklist-items` | `subskills/checklist-items/SKILL-MAIN.md` | The request provides one or more short lines that must become a Markdown checkbox list. |
| `title-case` | `subskills/title-case/SKILL-MAIN.md` | The request provides a title that must be converted to the fixed Title Case form. |

Use object notation such as `hmtest-demo-task->greet-name` to select a child. Load only the selected child's `SKILL-MAIN.md` and any resource that child names.

## Guardrails

- DO NOT load or execute more than one subskill for a single selected route.
- DO NOT add commentary to a child's exact-output result unless the user asks for it.
- DO NOT treat this fixture skill as a production-capable task suite.
