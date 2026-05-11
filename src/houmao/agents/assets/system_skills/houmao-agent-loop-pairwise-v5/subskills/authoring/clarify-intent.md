# Clarify Intent

Use this page when the user explicitly asks to `clarify intent` for one loop after the intention scaffold exists and the user has written initial source material.

This operation is a focused design interview. It clarifies intent, records accepted design decisions as ADRs, and updates editable intention files. It does not generate or repair `execplan/`.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`

Read first:
- `<loop-dir>/intention/loop-overview.md`
- directly relevant intention Markdown files
- existing `<loop-dir>/adrs/*.md` when present

If `<loop-dir>` or required intention files are missing, ask for the missing root or ask the user to run `create-intention` first.

## Decision Areas

Explore only the areas that are relevant to the current intention:
- objective, non-goals, and success posture
- participant roles and role instances
- collaboration topology and who may hand off work to whom
- mail/message families and structured communication needs
- on-event behaviors owned by each participant
- on-tick behaviors for scheduling, reconciliation, timeout, or completion checks
- harness responsibilities for data-model validation, dynamic lookup, query, rendering, and controlled record application
- runtime state and bookkeeping needs
- workspace, artifact, and evidence expectations, including whether the default Houmao `in-repo` workspace flavor plus loop bookkeeping dirs is sufficient
- completion, stop, override, and recovery posture

## Procedure

1. Read current intention source and existing ADRs.
2. Identify ambiguities, missing decisions, weak assumptions, or terms that need sharper meaning before execplan generation.
3. Ask exactly one focused decision question at a time.
4. Include a recommended answer when there is enough context to recommend one, and explain which intention files and future execplan surfaces the answer affects.
5. If the answer is already discoverable from existing intention or ADR files, use that source instead of asking the user.
6. When the user accepts, edits, or rejects the recommendation, record the accepted decision as a new ADR under `<loop-dir>/adrs/`.
7. Update `<loop-dir>/intention/loop-overview.md` when the decision affects the top-level objective, participants, lifecycle, or operating model.
8. Update or create focused intention Markdown files when the decision is too detailed for the overview, such as `participants.md`, `workflow.md`, `communication.md`, `state.md`, `harness.md`, `workspace.md`, or `constraints.md`.
9. Ensure every accepted ADR is reflected in at least one intention file.
10. If an existing `execplan/` may now be stale, report that it should be regenerated later; do not edit `execplan/` from this operation.
11. Continue with the next most important question only when useful; stop when the current decision thread is complete or the user pauses.

## ADR Shape

Use sequential numeric filenames:

```text
<loop-dir>/adrs/0001-short-decision-slug.md
<loop-dir>/adrs/0002-short-decision-slug.md
```

Use this Markdown structure:

```markdown
# ADR 0001: Short Decision Title

## Status

Accepted

## Context

Why the question matters for this loop.

## Decision

The accepted answer.

## Consequences

- What this changes in intention source.
- Which future execplan surfaces are likely affected.
- Any unresolved follow-up questions.
```

Keep ADRs concise. Do not create ADRs for minor wording edits that do not change intent, behavior, or generated-contract direction.

## Question Style

Ask one decision question, not a questionnaire dump.

Good shape:

```text
Question: Should this loop use mail for participant handoffs, a tick-driven scheduler, or both?

Recommended answer: Use mail for cross-participant handoffs and a lead-owned tick for scheduling and completion checks. That keeps handoffs auditable while keeping dynamic scheduling out of mail-received handlers.

If accepted, I will record an ADR and update `workflow.md` plus `loop-overview.md`.
```

## Boundaries

- Do not generate, repair, or directly edit `execplan/`.
- Do not require ADRs for `create-intention`; ADRs are created by this clarify operation after the user has initial intent source.
- Do not ask a large checklist of questions at once.
- Do not rewrite user-authored freeform files into a rigid template.
- Do not invent domain-specific policy that the user did not accept.
- Do not treat an ADR as accepted until the user accepts or edits the decision.
- Do not live-migrate active runs or generated agents from this operation.
