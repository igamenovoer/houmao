# Clarify Intent

## Read First

- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

## Preconditions

- User explicitly asks to `clarify intent` for one loop.
- The intention scaffold exists.
- The user has written initial source material.
- Goal:
  - clarify intent;
  - record accepted design decisions as ADRs;
  - update editable intention files.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`

Read first:
- `<loop-dir>/intention/loop-overview.md`
- directly relevant intention Markdown files
- existing `<loop-dir>/adrs/*.md` when present

Missing input rule:
- If `<loop-dir>` or required intention files are missing, ask for the missing root or ask the user to run `init` or `create-intention` first.

## Decision Areas

Explore only the areas that are relevant to the current intention:
- objective, non-goals, and success posture
- participant roles and role instances
- collaboration topology and who may hand off work to whom
- mail/message families, participant routes, structured payload fields, reply expectations, and mail-caused state or record effects
- on-event behaviors owned by each participant
- on-tick behaviors for scheduling, reconciliation, timeout, or completion checks
- loop-specific mail notification prompt instructions, including whether a tick should run after mail processing
- harness responsibilities for data-model validation, dynamic lookup, query, rendering, and controlled record application
- runtime state and bookkeeping needs
- workspace, artifact, and evidence expectations, including whether the default Houmao `in-repo` workspace flavor plus loop bookkeeping dirs is sufficient
- completion, stop, override, and recovery posture

## Communication Clarification

- Apply the default mail model from `runtime-mail-model.md`.
- Clarify only loop-specific communication decisions:
  - sender and recipient roles;
  - message families or templates;
  - structured payload fields;
  - reply expectations;
  - state, record, aggregation, or scheduling effects;
  - tick-after-mail needs;
  - loop-specific notifier prompt instructions.
- Do not ask the user to design Houmao mailbox, gateway, or managed-agent messaging mechanics unless the intention source explicitly rejects maintained Houmao surfaces.

## Actions

1. Read current intention source and existing ADRs.
2. Identify ambiguities, missing decisions, weak assumptions, or terms that need sharper meaning before execplan generation.
3. Ask exactly one focused decision question at a time.
4. Include a recommended answer when there is enough context to recommend one, and explain which intention files and future execplan surfaces the answer affects.
5. If the answer is already discoverable from existing intention or ADR files, use that source instead of asking the user.
6. When the user accepts, edits, or rejects the recommendation, record the accepted decision as a new ADR under `<loop-dir>/adrs/`.
7. Update `<loop-dir>/intention/loop-overview.md` when the decision affects the top-level objective, participants, lifecycle, or operating model.
8. Update or create focused intention Markdown files when the decision is too detailed for the overview, such as `participants.md`, `workflow.md`, `communication.md`, `state.md`, `harness.md`, `workspace.md`, or `constraints.md`.
9. Ensure every accepted ADR is reflected in at least one intention file.
10. If an existing `execplan/` may now be stale, report that it should be updated later with `update-execplan`; do not edit `execplan/` from this operation.
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

Rules:
- Keep ADRs concise.
- Do not create ADRs for minor wording edits that do not change intent, behavior, or generated-contract direction.

## Question Style

- Ask one decision question, not a questionnaire dump.
- Include:
  - the decision question;
  - a recommended answer when context supports one;
  - affected intention files;
  - likely future execplan surfaces.

Good shape:

```text
Question: For the work-request handoff from the coordinator role to the worker role, should the request require a structured result reply, a receipt-only acknowledgement, or no reply?

Recommended answer: Require a structured result reply and allow a receipt-only acknowledgement only for deferred work.
That gives the generated execplan a request-to-reply schema link while keeping scheduling and completion checks in a coordinator-owned tick.

If accepted, I will record an ADR and update `communication.md`, `workflow.md`, and `loop-overview.md`.
```

## Constraints

- Do not generate, repair, or directly edit `execplan/`.
- Do not require ADRs for `create-intention`; ADRs are created by this clarify operation after the user has initial intent source.
- Do not ask a large checklist of questions at once.
- Do not rewrite user-authored freeform files into a rigid template.
- Do not invent domain-specific policy that the user did not accept.
- Do not treat an ADR as accepted until the user accepts or edits the decision.
- Do not live-migrate active runs or generated agents from this operation.
