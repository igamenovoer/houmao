# Clarify Execplan

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Actions` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/markdown-contract-defaults.md](../../references/markdown-contract-defaults.md)
- [../../references/markdown-template-events.md](../../references/markdown-template-events.md)
- [../../references/direct-sqlite-state.md](../../references/direct-sqlite-state.md)
- [../../references/runtime-mail-model.md](../../references/runtime-mail-model.md)
- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)

## Inputs

Require:
- `<loop-dir>`
- generated lite `execplan/` material

## Chat Visuals

When showing generated Markdown, template, SQLite state, generated skill, agent-binding, coverage, or implementation shape directly in the chat session:

- Use fenced `text` code blocks or plain monospaced ASCII/text diagrams.
- Prefer simple ASCII characters such as `+---+`, `|`, and `->` so provider TUI chat can display the diagram without Mermaid rendering support.
- Do not use fenced `mermaid` code blocks for chat visual summaries.
- This chat-output rule does not change generated lite execplan artifact behavior.
- Mark unknown, contradictory, or stale parts as `Unknown`, `Contradictory`, or `Stale`; do not invent hidden policy.

## Actions

1. Read generated Markdown contracts, templates, state README/schema, generated skills, and agent bindings.
2. Identify implementation-level ambiguity or contradiction.
3. Ask one high-impact question at a time; prefer questions that unblock validation or execution readiness.
4. Update affected generated Markdown files after accepted answers.
5. If the ambiguity belongs to user intent, send the operator back to `clarify-intent` or intention edits.

## Constraints

- Do not introduce JSON schemas, Jinja2, harness commands, or generated docs.
- Do not patch around unresolved intent by inventing hidden policy.
