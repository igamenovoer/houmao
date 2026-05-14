# Clarification Protocol

## Purpose

Use this page before any clarification operation. It defines how to find high-impact ambiguity, ask bounded questions, record accepted answers, and update the correct source artifacts.

## Required Posture

- Read required source artifacts before asking questions.
- Read `runtime-mail-model.md` before clarifying any mail-driven loop behavior.
- Build an internal coverage map before asking the first question.
- Ask at most five accepted questions per session.
- Ask exactly one question at a time.
- Prefer questions that reduce downstream rework or prevent unsafe runtime behavior.
- Do not ask local wording, formatting, or file-placement questions while core loop logic remains unclear.

## Coverage Scan

For each operation-specific category, mark status internally:

- `Clear`: enough information exists for generation, validation, or execution.
- `Partial`: some facts exist, but important decisions remain unclear.
- `Missing`: expected facts are absent.
- `Deferred`: question matters but is better answered by a later operation or source authority.
- `Not applicable`: category does not apply to this loop.

Use the coverage map to create an internal candidate-question queue. Do not show the raw map before asking questions unless there are no meaningful questions.

## Prioritization

Select questions by impact times uncertainty. Favor questions that affect:

- process topology or phase order;
- mail/message semantics;
- event or tick ownership;
- state transitions and ownership;
- scheduling, completion, recovery, or stop behavior;
- generated contract shape;
- harness command behavior;
- agent binding and notifier prompt behavior;
- validation, evidence, or operator acceptance.

Exclude questions when:

- the answer is already discoverable from source artifacts;
- the answer would only change wording;
- the answer would not materially affect generation, validation, runtime safety, or acceptance;
- the question belongs to a different source authority.

## Question Format

If a clarification question asks for Houmao runtime or artifact-location input, use the required/optional shape from `system-input-questions.md`. Do not require that shape for user-task or domain-intent questions about objective, acceptance criteria, participant reasoning, algorithm choices, content scope, or business semantics unless the question is specifically about Houmao runtime behavior.

Each question must be answerable by one of:

- multiple choice with two to five mutually exclusive options;
- a constrained short answer, no more than five words.

For multiple choice:

- recommend one option when context supports it;
- explain the recommendation in one or two sentences;
- show options in a Markdown table;
- tell the user they can reply with the option letter, `yes`, `recommended`, or a short alternative.

For short answer:

- suggest an answer when context supports it;
- explain the suggestion in one sentence;
- tell the user they can reply with `yes`, `suggested`, or a short alternative.

## Answer Handling

- Treat `yes`, `recommended`, or `suggested` as acceptance of the current recommendation.
- If the answer is ambiguous, ask a quick disambiguation and do not advance to a new question.
- Do not treat a decision as accepted until the user accepts, edits, or supplies a valid answer.
- Stop when:
  - all critical ambiguities are resolved;
  - the user says to stop, proceed, or ask no more;
  - five accepted questions have been reached.

## Integration

After each accepted answer:

- record the question and accepted answer in the operation-owned ADR area;
- update the most appropriate source artifacts immediately;
- remove or replace contradictory old statements;
- preserve unrelated source structure;
- keep the inserted clarification minimal and testable;
- report if downstream artifacts are now stale.

## Validation

After each accepted answer:

- confirm exactly one ADR entry or file records the accepted answer;
- confirm the affected source artifacts reflect the accepted answer;
- confirm the ambiguity the answer was meant to resolve is not still present;
- confirm no now-contradictory alternative remains;
- confirm no source-authority boundary was crossed.

## Final Report

When the session ends, report:

- number of accepted questions;
- ADR files or entries created;
- source artifacts updated;
- stale downstream artifacts, if any;
- concise coverage summary with `Clear`, `Resolved`, `Deferred`, and `Outstanding` categories;
- recommended next operation.
