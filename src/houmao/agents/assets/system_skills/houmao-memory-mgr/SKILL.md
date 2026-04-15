---
name: houmao-memory-mgr
description: "Use when the user's intent is to read or write a Houmao-managed agent's `houmao-memo.md` file or a launch profile's Houmao memo seed. Necessary trigger: `memo` is mentioned. Sufficient trigger: the prompt or context says `houmao memo`, says `agent memo` where the agent clearly refers to a Houmao-managed agent, or asks for a launch/easy profile memo seed. An explicit reference to `houmao-memo.md` is a very strong hint to call this skill."
license: MIT
---

# Houmao Memory Manager

Use this Houmao skill only when the necessary trigger condition is met:

- the prompt or recent context mentions `memo`

The sufficient trigger conditions are:

- the prompt or recent context says `houmao memo`
- the prompt or recent context says `agent memo`, and that agent clearly refers to a Houmao-managed agent
- the prompt or recent context asks for a launch profile, easy profile, or reusable profile memo seed

When triggered, handle requests to edit, add something to, remove something from, inspect, or otherwise manage the Houmao/agent memo, a launch profile's Houmao memo seed, or memo-linked managed-agent memory pages.

## Scope

This skill covers only Houmao-managed memo surfaces:

- `houmao-mgr agents memory path|status`
- `houmao-mgr agents memory memo show|set|append`
- `houmao-mgr agents memory tree|resolve|read|write|append|delete`
- launch-profile memo seeds on reusable birth-time profiles:
  - easy-profile lane: `houmao-mgr project easy profile create|get|set`
  - explicit launch-profile lane: `houmao-mgr project agents launch-profiles add|get|set`
  - memo seed source options: `--memo-seed-text`, `--memo-seed-file`, and `--memo-seed-dir`
  - memo seed policy and clearing options: `--memo-seed-policy` and `--clear-memo-seed`
- live-session environment variables `HOUMAO_AGENT_MEMORY_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_PAGES_DIR`

It does not cover provider-native memory, mailbox state, gateway reminders, runtime manifests, task queues, or arbitrary work artifacts.

## Workflow

1. Determine the target kind before choosing an edit surface:
   - If the prompt or recent context clearly says the user is working with a reusable launch profile, easy profile, profile defaults, birth-time config, future launches, or `--launch-profile`/`--profile`, update that launch profile's Houmao memo seed. Do not mutate any live agent memo for that request.
   - Otherwise, treat the request as a live managed-agent memory request. If the request is about the current managed agent, prefer `HOUMAO_AGENT_MEMO_FILE` and `HOUMAO_AGENT_PAGES_DIR`. If it names another managed agent, use `houmao-mgr agents memory path --agent-name <name>` or `--agent-id <id>` to find the memo and pages paths.
2. Choose one `houmao-mgr` launcher for this turn:
   - first use `command -v houmao-mgr` when available
   - otherwise use `uv tool run --from houmao houmao-mgr`
   - only then use a development launcher such as `pixi run houmao-mgr`, `.venv/bin/houmao-mgr`, or `uv run houmao-mgr`
3. For a launch-profile memo seed, identify the lane:
   - easy profile: create, inspect, or update with `project easy profile create|get|set --name <profile>`
   - explicit recipe-backed launch profile: create, inspect, or update with `project agents launch-profiles add|get|set --name <profile>`
   - if the lane is ambiguous after checking prompt and context, ask whether the user means an easy profile or an explicit launch profile before editing.
4. For a launch-profile memo seed edit, read the profile first, then use exactly one memo seed source when setting content:
   - `--memo-seed-text <text>` for short inline memo content
   - `--memo-seed-file <path>` for one Markdown file whose content becomes `houmao-memo.md`
   - `--memo-seed-dir <path>` for a memo-shaped directory containing `houmao-memo.md` and/or `pages/`
5. Use `--memo-seed-policy initialize|replace|fail-if-nonempty` when the user requests launch-time application behavior. Memo seed policies apply only to the managed-memory components represented by the seed source: text and file seeds touch only `houmao-memo.md`, while directory seeds touch `houmao-memo.md` only when that file is present and pages only when `pages/` is present. If the user supplies seed content without a policy, rely on the default `initialize` policy. Use `--clear-memo-seed` when the user asks to remove stored seed configuration. Never combine `--clear-memo-seed` with a seed source or seed policy.
6. Do not use prompt overlays as a substitute for memo seeds. Prompt overlays shape launch prompts; memo seeds materialize durable `houmao-memo.md` and contained `pages/` content before a profile-backed launch starts.
7. For a live managed-agent edit, read before editing. Use `agents memory memo show` for the fixed memo and `agents memory read --path <page>` for a page.
8. For live memo edits, keep the smallest meaningful change. Prefer `memo append` for simple additions; for removals or rewrites, replace the full memo with `memo set` after preserving unrelated text.
9. For live supporting pages, use `tree`, `resolve`, `read`, `write`, `append`, and `delete` with a `--path` relative to `pages/`.
10. When a live memo should reference a page, author a normal Markdown link such as `[run notes](pages/notes/run.md)`; use `resolve --path <page>` when you need the exact memo-relative link or absolute page path.

## Guardrails

- Treat `houmao-memo.md` as free-form Markdown owned by the operator and agent.
- Treat a launch-profile memo seed as birth-time configuration for future launches from that profile. It is not the same thing as a live session's current `houmao-memo.md`.
- Treat `--memo-seed-text '' --memo-seed-policy replace` as an intentional empty memo seed for future launches, not as a request to clear pages. Treat `--clear-memo-seed` as removal of stored seed configuration, not as a way to write an empty memo.
- If prompt or context clearly points at a launch profile or easy profile, do not run `houmao-mgr agents memory ...`; update the stored profile memo seed instead.
- Do not generate, refresh, sort, validate, or remove page indexes inside the memo unless the user asks for that exact content edit.
- Do not use absolute page paths or `..`; page operations must stay inside the managed `pages/` directory.
- For `--memo-seed-dir`, use only memo-shaped directories with supported top-level entries `houmao-memo.md` and `pages/`; do not use arbitrary directory trees as memo seeds.
- Do not write arbitrary files beside `houmao-memo.md` at the memory root.
- Do not store live runtime bookkeeping, retry counters, mailbox receipts, gateway state, or supervision state in managed memory pages.
- Do not hand-edit `.houmao/agents/launch-profiles/<name>.yaml` when the maintained profile `create|add|set` command exposes memo seed operations.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints.
