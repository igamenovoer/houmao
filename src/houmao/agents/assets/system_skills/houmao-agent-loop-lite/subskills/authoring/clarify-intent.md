# Clarify Intent

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

## Actions

1. Read intention Markdown and existing accepted decisions when present.
2. Build a coverage map for objective, participants, communication, process, state, workspace, run artifacts, controls, and acceptance.
3. Ask only high-impact questions that affect generated Markdown contracts, templates, skills, SQLite state, or runtime safety.
4. Ask one question at a time; stop after at most five accepted answers in one session.
5. Record accepted answers in editable intention Markdown or intention ADRs when the project already uses them.
6. Do not edit `execplan/` from this page.

## Report

Summarize clarified intent, remaining blockers, and whether `execplan-fast-forward` can proceed.
