---
name: houmao-memory-mgr
description: "Use when the user's intent is to read or write a Houmao-managed agent's `houmao-memo.md` file. Necessary trigger: `memo` is mentioned. Sufficient trigger: the prompt or context says `houmao memo`, or says `agent memo` where the agent clearly refers to a Houmao-managed agent. An explicit reference to `houmao-memo.md` is a very strong hint to call this skill."
license: MIT
---

# Houmao Memory Manager

Use this Houmao skill only when the necessary trigger condition is met:

- the prompt or recent context mentions `memo`

The sufficient trigger conditions are:

- the prompt or recent context says `houmao memo`
- the prompt or recent context says `agent memo`, and that agent clearly refers to a Houmao-managed agent

When triggered, handle requests to edit, add something to, remove something from, inspect, or otherwise manage the Houmao/agent memo or memo-linked managed-agent memory pages.

## Scope

This skill covers only the managed-agent memory surface:

- `houmao-mgr agents memory path|status`
- `houmao-mgr agents memory memo show|set|append`
- `houmao-mgr agents memory tree|resolve|read|write|append|delete`
- live-session environment variables `HOUMAO_AGENT_MEMORY_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_PAGES_DIR`

It does not cover provider-native memory, mailbox state, gateway reminders, runtime manifests, task queues, or arbitrary work artifacts.

## Workflow

1. Determine the target agent. If the request is about the current managed agent, prefer `HOUMAO_AGENT_MEMO_FILE` and `HOUMAO_AGENT_PAGES_DIR`. If it names another managed agent, use `houmao-mgr agents memory path --agent-name <name>` or `--agent-id <id>` to find the memo and pages paths.
2. Choose one `houmao-mgr` launcher for this turn:
   - first use `command -v houmao-mgr` when available
   - otherwise use `uv tool run --from houmao houmao-mgr`
   - only then use a development launcher such as `pixi run houmao-mgr`, `.venv/bin/houmao-mgr`, or `uv run houmao-mgr`
3. Read before editing. Use `agents memory memo show` for the fixed memo and `agents memory read --path <page>` for a page.
4. For memo edits, keep the smallest meaningful change. Prefer `memo append` for simple additions; for removals or rewrites, replace the full memo with `memo set` after preserving unrelated text.
5. For supporting pages, use `tree`, `resolve`, `read`, `write`, `append`, and `delete` with a `--path` relative to `pages/`.
6. When a memo should reference a page, author a normal Markdown link such as `[run notes](pages/notes/run.md)`; use `resolve --path <page>` when you need the exact memo-relative link or absolute page path.

## Guardrails

- Treat `houmao-memo.md` as free-form Markdown owned by the operator and agent.
- Do not generate, refresh, sort, validate, or remove page indexes inside the memo unless the user asks for that exact content edit.
- Do not use absolute page paths or `..`; page operations must stay inside the managed `pages/` directory.
- Do not write arbitrary files beside `houmao-memo.md` at the memory root.
- Do not store live runtime bookkeeping, retry counters, mailbox receipts, gateway state, or supervision state in managed memory pages.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints.
