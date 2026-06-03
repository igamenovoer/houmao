---
name: houmao-memory-mgr
description: "Use when the user's intent is to read or write a Houmao-managed agent's `houmao-memo.md` file or a reusable profile's Houmao memo seed. Necessary trigger: `memo` is mentioned. Sufficient trigger: the prompt or context says `houmao memo`, says `agent memo` where the agent clearly refers to a Houmao-managed agent, or asks for an easy/launch dossier memo seed. An explicit reference to `houmao-memo.md` is a very strong hint to call this skill."
license: MIT
---

# Houmao Memory Manager

Use this Houmao skill only when the necessary trigger condition is met:

- the prompt or recent context mentions `memo`

The sufficient trigger conditions are:

- the prompt or recent context says `houmao memo`
- the prompt or recent context says `agent memo`, and that agent clearly refers to a Houmao-managed agent
- the prompt or recent context asks for a launch dossier, project profile, or reusable profile memo seed

When triggered, handle requests to edit, add something to, remove something from, inspect, or otherwise manage the Houmao/agent memo, a reusable profile's Houmao memo seed, or memo-linked managed-agent memory pages.

## Help

When the user asks `$houmao-memory-mgr help`, `help for houmao-memory-mgr`, `usage for houmao-memory-mgr`, `available functionality for houmao-memory-mgr`, or what this skill can do, answer from this section before choosing a live-memory or launch dossier memo-seed workflow, command, or missing-input question. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me append this to the agent memo", route to the matching workflow instead of stopping at generic help.

Purpose: read and update Houmao-managed memo surfaces for live agents and reusable profile memo seeds.

Available functionality:

- Inspect, set, or append the fixed live `houmao-memo.md`.
- Read, write, append, delete, resolve, and list memo-linked pages under `pages/`.
- Locate live managed-agent memory paths.
- Create, update, or clear project profile and launch-dossier memo seeds for future launches.

Common starting prompts:

- `$houmao-memory-mgr help`
- `$houmao-memory-mgr show memo for <agent>`
- `$houmao-memory-mgr append to <agent> memo`
- `$houmao-memory-mgr set memo seed for profile <name>`

Related skills and boundaries:

- Use `houmao-agent-definition` for non-memory profile authoring.
- Use `houmao-agent-inspect` for runtime manifests, logs, screen, or mailbox posture.
- Use `houmao-agent-gateway` for reminders, not managed memory.
- Do not use this skill for provider-native memory, mailbox state, task queues, or arbitrary work artifacts.

## Scope

This skill covers only Houmao-managed memo surfaces:

- `help` (read-only meta operation)
- current-session live memory: `houmao-mgr agents self memory path|status`
- current-session memo operations: `houmao-mgr agents self memory memo show|set|append`
- current-session page operations: `houmao-mgr agents self memory tree|resolve|read|write|append|delete`
- selected-agent live memory: `houmao-mgr agents single --agent-name <name> memory ...` or `houmao-mgr agents single --agent-id <id> memory ...`
- launch dossier memo seeds on reusable birth-time profiles:
  - project profile lane: `houmao-mgr project profile create|get|set`
  - launch-dossier lane: `houmao-mgr internals native-agent launch-dossiers add|get|set`
  - memo seed source options: `--memo-seed-text`, `--memo-seed-file`, and `--memo-seed-dir`
  - clearing option: `--clear-memo-seed`
- live-session environment variables `HOUMAO_AGENT_MEMORY_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_PAGES_DIR`

It does not cover provider-native memory, mailbox state, gateway reminders, runtime manifests, task queues, or arbitrary work artifacts.

## Workflow

Before starting the workflow, answer explicit skill-help intent from `## Help` and stop.

1. Determine the target kind before choosing an edit surface:
   - If the prompt or recent context clearly says the user is working with a reusable launch profile, project profile, profile defaults, birth-time config, future launches, or `--launch-profile`/`--profile`, update that launch profile's Houmao memo seed. Do not mutate any live agent memo for that request.
   - Otherwise, treat the request as a live managed-agent memory request. If the request is about the current managed agent, prefer `HOUMAO_AGENT_MEMO_FILE` and `HOUMAO_AGENT_PAGES_DIR`; when those are unavailable inside a managed session, use `houmao-mgr agents self memory path`. If it names another managed agent, use `houmao-mgr agents single --agent-name <name> memory path` or `houmao-mgr agents single --agent-id <id> memory path` to find the memo and pages paths.
2. Choose one `houmao-mgr` launcher for this turn:
   - first use `command -v houmao-mgr` when available
   - otherwise use `uv tool run --from houmao houmao-mgr`
   - only then use a development launcher such as `pixi run houmao-mgr`, `.venv/bin/houmao-mgr`, or `uv run houmao-mgr`
3. For a launch dossier memo seed, identify the lane:
   - project profile: inspect directly when needed, then create or update through `project.profile.create` or `project.profile.set`
   - launch dossier: inspect directly when needed, then create or update through `internals.native-agent.launch-dossiers.add` or `internals.native-agent.launch-dossiers.set`
   - if the lane is ambiguous after checking prompt and context, ask whether the user means a project profile or a launch dossier before editing.
4. For a launch dossier memo seed edit, read the profile first, then use the maintained profile `set` command with exactly one memo seed source when setting content:
   - `--memo-seed-text <text>` for short inline memo content
   - `--memo-seed-file <path>` for one Markdown file whose content becomes `houmao-memo.md`
   - `--memo-seed-dir <path>` for a memo-shaped directory containing `houmao-memo.md` and/or `pages/`
5. Do not pass memo seed fields to `internals config-drafts generate`; config drafts are minimal profile authoring aids that accept only name/source/credential holes. Live memory commands remain direct skill guidance and are not profile config-draft commands.
6. Memo seeds always replace only the managed-memory components represented by the seed source: text and file seeds touch only `houmao-memo.md`, while directory seeds touch `houmao-memo.md` only when that file is present and pages only when `pages/` is present. Use `--clear-memo-seed` when the user asks to remove stored seed configuration. Never combine `--clear-memo-seed` with a seed source.
7. Do not use prompt overlays as a substitute for memo seeds. Prompt overlays shape launch prompts; memo seeds materialize durable `houmao-memo.md` and contained `pages/` content before a profile-backed launch starts.
8. For a live managed-agent edit, read before editing. Use `agents self memory memo show` or `agents single ... memory memo show` for the fixed memo, and `agents self memory read --path <page>` or `agents single ... memory read --path <page>` for a page.
9. For live memo edits, keep the smallest meaningful change. Prefer `memo append` for simple additions; for removals or rewrites, replace the full memo with `memo set` after preserving unrelated text.
10. For live supporting pages, use `tree`, `resolve`, `read`, `write`, `append`, and `delete` with a `--path` relative to `pages/`.
11. When a live memo should reference a page, author a normal Markdown link such as `[run notes](pages/notes/run.md)`; use `resolve --path <page>` when you need the exact memo-relative link or absolute page path.

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If the target kind, managed-agent selector, profile lane, profile name, memo path, page path, or mutation text is still missing, ask before editing.
- When asking for Houmao memo-system inputs, use readable Markdown:
  - separate `Required` values from `Optional` modifiers
  - `Required`: values that block the selected memory command or profile memo-seed edit
  - `Optional`: launcher preference, profile lane defaults, seed source choice, page-path detail, output format, or skip choices; if none apply, say `Optional: none for this step.`
  - use a short bullet list when only one or two required fields are missing
  - use a compact table when the target kind, lane, or several required fields need clarification
- Do not use this format for the user's memo content itself unless the question is about Houmao runtime behavior.

## Guardrails

- Treat `houmao-memo.md` as free-form Markdown owned by the operator and agent.
- Treat a launch dossier memo seed as birth-time configuration for future launches from that profile. It is not the same thing as a live session's current `houmao-memo.md`.
- Treat `--memo-seed-text ''` as an intentional empty memo seed for future launches, not as a request to clear pages. Treat `--clear-memo-seed` as removal of stored seed configuration, not as a way to write an empty memo.
- If prompt or context clearly points at a launch profile or project profile, do not run live `houmao-mgr agents self memory ...` or `houmao-mgr agents single ... memory ...` commands; update the stored profile memo seed instead.
- Do not generate, refresh, sort, validate, or remove page indexes inside the memo unless the user asks for that exact content edit.
- Do not use absolute page paths or `..`; page operations must stay inside the managed `pages/` directory.
- For `--memo-seed-dir`, use only memo-shaped directories with supported top-level entries `houmao-memo.md` and `pages/`; do not use arbitrary directory trees as memo seeds.
- Do not write arbitrary files beside `houmao-memo.md` at the memory root.
- Do not store live runtime bookkeeping, retry counters, mailbox receipts, gateway state, or supervision state in managed memory pages.
- Do not hand-edit `.houmao/agents/launch-profiles/<name>.yaml` when the maintained profile `create|add|set` command exposes memo seed operations.
- Do not hand-author profile memo-seed YAML skeletons; use maintained profile `set` memo-seed fields and leave omitted profile defaults omitted.
- Do not use deprecated `houmao-cli` or removed standalone CAO launcher workflows.
