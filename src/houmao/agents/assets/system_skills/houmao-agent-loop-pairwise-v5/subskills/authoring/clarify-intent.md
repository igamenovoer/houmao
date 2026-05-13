# Clarify Intent

## Read First

- `../reference/clarification-protocol.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

## Preconditions

- User asks for `clarify-intent` or clearly asks to clarify loop intent.
- The intention scaffold exists.
- The user has written initial source material.
- Goal:
  - clarify intended loop behavior;
  - record accepted intent decisions as ADRs;
  - update editable intention files.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`

Read before asking:
- `<loop-dir>/intention/loop-overview.md`
- `<loop-dir>/intention/project-context.md` when present
- directly relevant intention Markdown files
- existing `<loop-dir>/adrs/*.md` when present

Missing input rule:
- If `<loop-dir>` or required intention files are missing, ask for the missing root or ask the user to run `init` or `create-intention` first.

## Coverage Scan

Build an internal coverage map before asking. Use these intent categories:

- objective, non-goals, success posture, acceptance authority, and terminal conditions;
- agent communication: participants, routes, message families, handoff rights, reply expectations, escalation, and default transport assumptions;
- loop process: phases, topology, work-item lifecycle, event triggers, on-event responsibilities, on-tick responsibilities, scheduling, timeout, recovery, and completion flow;
- state/bookkeeping needs and ownership facts;
- operator controls: pause, resume, stop, override, repair, and recovery;
- workspace, artifact, evidence, and run-output expectations;
- project integration context from `project-context.md` or nearby project facts already captured;
- terminology, canonical nouns, and ambiguous adjectives;
- explicit omissions and out-of-scope behavior.

Question priority:

1. Resolve objective ambiguity first: what the loop is trying to achieve, what is out of scope, how success is accepted, and when the loop is done.
2. Resolve agent communication ambiguity next: who talks to whom, through what message families, with what reply expectations, and what handoff or escalation means.
3. Resolve loop process ambiguity next: how work moves through phases, what events/ticks advance it, what happens on timeout or failure, and how completion/recovery works.
4. Ask about state, operator controls, workspace, artifacts, evidence, project integration, terminology, or file organization only after the core objective, communication, and process shape is clear enough.

Prioritize questions whose answers affect generated process, contracts, runtime safety, scheduling, recovery, validation, or acceptance. Avoid low-impact local wording or file-organization questions while objective, agent communication, or loop process logic is partial or missing.

## Question Focus

Good intent questions confirm loop behavior, for example:

- What is the exact success condition the loop must reach?
- Which participant owns terminal acceptance?
- Which participants communicate directly, and what message family carries the handoff?
- What reply is expected after a work-request handoff?
- What event or tick should advance the loop after a reply arrives?
- What should happen when a reply is missing?
- Which facts must become durable state instead of mail prose?
- Which operator action may override normal scheduling?

Weak questions ask about wording, local headings, or template placement without changing loop behavior.

## Actions

1. Read current intention source, project context, and existing ADRs.
2. Apply `clarification-protocol.md` to build an internal coverage map and question queue.
3. Ask at most five accepted questions per session, exactly one at a time.
4. Include a recommended or suggested answer when context supports one.
5. If the answer is discoverable from current intention or ADRs, use that source instead of asking.
6. After each accepted answer:
  - create the next ADR under `<loop-dir>/adrs/`;
  - update `loop-overview.md` when the decision affects objective, participants, lifecycle, or operating model;
  - update or create focused intention Markdown such as `participants.md`, `workflow.md`, `communication.md`, `state.md`, `harness.md`, `workspace.md`, or `constraints.md`;
  - remove contradictory old text;
  - report if an existing `execplan/` is now stale.
7. Stop when critical ambiguities are resolved, the user pauses, or five accepted questions have been recorded.
8. Finish with the coverage summary required by `clarification-protocol.md`.

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

## Question

The clarification question that was asked.

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

## Constraints

- Do not generate, repair, or directly edit `execplan/`.
- Do not require ADRs for `create-intention`; ADRs are created by this clarify operation after the user has initial intent source.
- Do not ask a large checklist of questions at once.
- Do not rewrite user-authored freeform files into a rigid template.
- Do not invent domain-specific policy that the user did not accept.
- Do not treat an ADR as accepted until the user accepts or edits the decision.
- Do not live-migrate active runs or generated agents from this operation.
