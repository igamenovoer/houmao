# Clarify Intent

## Read First

- `../reference/clarification-protocol.md`
- `../reference/topology-modes.md`
- `../reference/cycle-normalization.md`
- `../reference/predecessor-context.md`
- `../reference/mail-schema-events.md`
- `../reference/result-routing.md`
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

- objective, non-goals, success posture, acceptance authority, objective parameters, hidden variables, and terminal conditions;
- topology mode: `tree-loop`, `generic-loop`, or unresolved; tree-loop normalization needs; generic predecessor-context posture;
- agent communication: participants, routes, message families, schema-id mail types, handoff rights, reply or forward expectations, escalation, and default transport assumptions;
- loop process: phases, topology, work-item lifecycle, event triggers, on-event responsibilities, on-tick responsibilities, scheduling, dedupe, timeout, recovery, and completion flow;
- state/bookkeeping needs and ownership facts;
- operator controls: pause, resume, stop, override, repair, and recovery;
- workspace, artifact, evidence, and run-output expectations;
- project integration context from `project-context.md` or nearby project facts already captured;
- terminology, canonical nouns, and ambiguous adjectives;
- explicit omissions and out-of-scope behavior.

Question priority:

1. Resolve objective ambiguity first: what the loop is trying to achieve, what parameters or assumptions define the objective, what is out of scope, how success is accepted, and when the loop is done.
2. Resolve topology ambiguity next: whether execution is `tree-loop` local-close or `generic-loop`, whether tree-loop cycles need normalization, and whether generic cycles need termination or dedupe rules.
3. Resolve agent communication ambiguity next: who talks to whom, through what schema-typed message families, with what context, reply, forward, or escalation expectations.
4. Resolve predecessor-context needs for generic routes: what selected upstream refs, summaries, artifacts, branches, commits, or state refs must be carried, or whether omission is explicit and safe.
5. Resolve loop process ambiguity next: how work moves through phases, what events/ticks advance it, what happens on timeout or failure, and how completion/recovery works.
6. Ask about state, operator controls, workspace, artifacts, evidence, project integration, terminology, or file organization only after the core objective, topology, communication, and process shape is clear enough.

Prioritize questions whose answers affect generated process, contracts, runtime safety, scheduling, recovery, validation, topology, or acceptance. Avoid low-impact local wording or file-organization questions while objective, topology, agent communication, predecessor context, or loop process logic is partial or missing.

## Visual Summary

Before asking the first clarification question, show a provisional high-level visual summary from the current intention source:

- an agent architecture Mermaid diagram that shows participant roles or concrete agents and their communication routes;
- a loop structure Mermaid diagram that shows major phases, events, handoffs, ticks, terminal posture, and recovery path when known.

Rules:

- Use fenced `mermaid` code blocks.
- Prefer `flowchart` for architecture and `sequenceDiagram` or `stateDiagram-v2` for loop structure.
- Mark unknown or unclear parts as `Unknown` or `TBD`; do not invent missing intent.
- Keep diagrams high level enough to fit in the clarification turn.
- Update the diagrams in the final coverage summary when accepted answers materially change architecture or loop structure.

## Question Focus

Good intent questions confirm loop behavior, for example:

- What is the exact success condition the loop must reach?
- Which participant owns terminal acceptance?
- Should this loop use `tree-loop` local-close handoffs or `generic-loop` directed routing?
- If tree-loop intent contains a closed loop, which existing participant should act as relay, root, or cycle breaker?
- Which participants communicate directly, and what message family carries the handoff?
- Which `schema_id` mail family represents the event that wakes this participant?
- What reply is expected after a work-request handoff?
- For this generic route, which predecessor refs or summaries must be carried downstream, if any?
- What event or tick should advance the loop after a reply arrives?
- What dedupe key or termination rule bounds a repeated generic route?
- What should happen when a reply is missing?
- Which facts must become durable state instead of mail prose?
- Which operator action may override normal scheduling?

Weak questions ask about wording, local headings, or template placement without changing loop behavior.

## Actions

1. Read current intention source, project context, and existing ADRs.
2. Apply `clarification-protocol.md` to build an internal coverage map and question queue.
3. Show the provisional high-level Mermaid agent architecture and loop structure diagrams.
4. Ask at most five accepted questions per session, exactly one at a time.
5. Include a recommended or suggested answer when context supports one.
6. If the answer is discoverable from current intention or ADRs, use that source instead of asking.
7. After each accepted answer:
  - create the next ADR under `<loop-dir>/adrs/`;
  - update `loop-overview.md` when the decision affects objective, participants, lifecycle, or operating model;
  - update or create focused intention Markdown such as `participants.md`, `workflow.md`, `communication.md`, `state.md`, `harness.md`, `workspace.md`, or `constraints.md`;
  - remove contradictory old text;
  - report if an existing `execplan/` is now stale.
8. Stop when critical ambiguities are resolved, the user pauses, or five accepted questions have been recorded.
9. Finish with the coverage summary required by `clarification-protocol.md`.

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
