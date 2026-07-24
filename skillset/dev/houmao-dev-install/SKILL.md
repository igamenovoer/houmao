---
name: houmao-dev-install
description: Use when a Houmao maintainer explicitly invokes this development skill to install or refresh the current checkout as an editable user-space uv tool with a commit-stamped local version, or to update packaged Houmao system skills and development-skill links in project-local Claude, Codex, Kimi Code, Copilot, or universal agent homes.
---

# Houmao Development Install

## Overview

Use this skill for development-only installation from the current Houmao checkout. Preserve source changes, keep the uv installation editable, and update project-local agent homes through Houmao's current config-backed system-skill lifecycle.

## When to Use

Use this skill when a maintainer wants `houmao-mgr` and `houmao-passive-server` to resolve to the current checkout, needs a commit-identifiable local build, or wants project-local agent skill roots refreshed from repository sources.

Do not use it for PyPI releases, ordinary Pixi environment setup, user-wide agent-skill installation, or managed-agent launch-time skill projection.

## Workflow

1. **Select the subcommand** from the **Subcommands** table. If the request names no actionable routine, handle `help` without changing the checkout or an agent home.
2. **Resolve the Houmao checkout** from the user-supplied path or current directory. Require Houmao's `pyproject.toml`, Git metadata, `skillset/dev/`, and packaged system-skill assets.
3. **Load the selected command page** and follow its workflow, including its preflight, restoration, ownership, and verification gates.
4. **Report the result** with the resolved checkout, exact targets, installed version or refreshed skills, verification evidence, and preserved worktree state.

If the request does not map cleanly to these steps, use the native planning tool to build and execute a bounded plan from the subcommands and constraints in this skill.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `install-to-uv` | Install or refresh the current checkout as an editable user-space uv tool with a temporary commit-stamped local version. | [commands/install-to-uv.md](commands/install-to-uv.md) |
| `update-project-skills` | Refresh packaged system-skill packs and selected `skillset/dev/` links in project-local agent homes. | [commands/update-project-skills.md](commands/update-project-skills.md) |
| `help` | Explain the two routines, their targets, defaults, ownership boundaries, and outputs without changing files. | This entrypoint |

## Guardrails

- DO NOT use this skill for releases, system-wide installation, or user-wide agent homes.
- DO NOT leave the temporary local version in `pyproject.toml`.
- DO NOT reset, clean, or replace a whole tracked file to restore the checkout.
- DO NOT treat an old `receipt.json` as current ownership evidence.
- DO NOT remove or replace an unowned skill directory without explicit user approval.
- DO NOT remove a development skill merely because the current request omits it.
