# Clarify Intent

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/markdown-contract-defaults.md`
- `../reference/markdown-template-events.md`
- `../reference/direct-sqlite-state.md`
- `../reference/runtime-mail-model.md`
- `../reference/system-input-questions.md`

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`

## Chat Visuals

When showing participants, routes, phases, unknowns, coverage, or loop shape directly in the chat session:

- Use fenced `text` code blocks or plain monospaced ASCII/text diagrams.
- Prefer simple ASCII characters such as `+---+`, `|`, and `->` so provider TUI chat can display the diagram without Mermaid rendering support.
- Do not use fenced `mermaid` code blocks for chat visual summaries.
- This chat-output rule does not change generated lite execplan artifact behavior.
- Mark unknown or unclear parts as `Unknown` or `TBD`; do not invent missing intent.

## Actions

1. Read intention Markdown and existing accepted decisions when present.
2. Build a coverage map for objective, participants, communication, process, state, workspace, run artifacts, controls, and acceptance.
3. Ask only high-impact questions that affect generated Markdown contracts, templates, skills, SQLite state, or runtime safety.
4. Ask one question at a time; stop after at most five accepted answers in one session.
5. Record accepted answers in editable intention Markdown or intention ADRs when the project already uses them.
6. Do not edit `execplan/` from this page.

## Report

Summarize clarified intent, remaining blockers, and whether `execplan-fast-forward` can proceed.
