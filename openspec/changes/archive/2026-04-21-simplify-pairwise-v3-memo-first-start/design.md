## Context

`houmao-agent-loop-pairwise-v3` was introduced as the workspace-aware extension of pairwise-v2, and it currently inherits pairwise-v2's heavier prestart and start structure. In the current design, `initialize` writes durable initialize pages plus memo reference blocks, while `start` writes a durable `start-charter` page, refreshes another memo reference block, and waits for an explicit `accepted` or `rejected` reply from the designated master.

That structure makes v3 harder to operate than necessary for its main use case. The same run contract is spread across plan files, initialize pages, memo pointers, and a start charter, even though agents naturally consult memo material during execution. The proposed change simplifies the v3 lifecycle by making per-agent memo materialization the canonical prestart contract and reducing `start` to a compact kickoff trigger after `initialize` is complete.

This is a cross-cutting change inside the packaged skill assets because it affects `SKILL.md`, authoring guidance, plan templates, prestart guidance, start guidance, and docs that currently describe v3 as inheriting the pairwise-v2 start handshake.

## Goals / Non-Goals

**Goals:**

- Make pairwise-v3 `initialize` the single canonical step that materializes per-agent run guidance.
- Let pairwise-v3 `initialize` launch missing participants when the plan provides launch profiles for them.
- Store organization rules, goals, workspace posture, and local obligations directly in the relevant agents' memo surfaces instead of page-backed initialize material.
- Make ordinary pairwise-v3 `start` a small "read your memo and start" trigger to the designated master.
- Send that ordinary `start` trigger through mail by default, with direct prompt only as an explicit user override.
- Remove the ordinary `start` requirement for explicit `accepted` or `rejected` replies.
- Keep the authored workspace contract and routing-packet structure available to runtime agents without asking them to recompute topology.
- Fail closed before `ready` or recovery resumption when any required participant lacks email/mailbox support.

**Non-Goals:**

- Redesign pairwise-v2 or the stable pairwise skill.
- Remove the authored workspace contract from pairwise-v3 plans.
- Eliminate routing packets or other plan-time dispatch structure from pairwise-v3.
- Redesign `recover_and_continue` in this change beyond any reference updates required to stay coherent with the new start model.

## Decisions

### Decision: Pairwise-v3 `initialize` becomes memo-first and page-light

`initialize` will become the canonical step that writes run-owned memo blocks for the designated master and related participants. Those memo blocks will contain the durable instructions that participants need before execution: organization rules, goals, local obligations, workspace posture, and routing/dispatch guidance appropriate to that participant.

We will not keep the current initialize-page-plus-pointer pattern as the default v3 contract. The point of the v3 revision is to make memo materialization itself the durable handoff.

Alternatives considered:

- Keep initialize pages and only simplify `start`.
  This would preserve more v2 structure, but it would keep the main duplication problem in place.
- Replace memo materialization with mailbox-only prestart mail.
  This would make the durable contract harder to rediscover and less aligned with the managed-memory model already used elsewhere in Houmao.

### Decision: `initialize` may launch missing participants from provided launch profiles

If the authored plan provides launch-profile references for required participants, `initialize` may use those profiles to launch missing participants before email/mailbox verification and memo materialization. It should inspect the launch profile's mailbox association first and fail closed before launch when the profile does not declare the mailbox support the run requires. This keeps the operational contract compact: the same step that prepares the run may also bring the named team into existence when the operator already declared how those agents should be born.

If a required participant is still missing and no launch profile was provided for it, `initialize` fails closed instead of inventing a launch lane or silently skipping that participant.

Alternatives considered:

- Require operators to launch every participant manually before `initialize`.
  This keeps lifecycle concerns more separate, but it makes the v3 run contract less self-sufficient and adds repetitive preflight work the plan could already specify.

### Decision: `start` becomes a compact kickoff trigger to the master only

Ordinary `start` will no longer write a durable `start-charter` page or wait for `accepted` / `rejected`. Once `initialize` has completed and the run is ready, `start` will send a short trigger to the designated master telling it to read its memo and begin work.

The trigger remains master-only. The master remains the run owner after `start`, and workers begin when the master dispatches to them using the prepared run material.

Ordinary delivery should use Houmao mail by default rather than direct prompt injection. That keeps the kickoff aligned with the same mailbox-first communication posture the run uses afterward. Direct prompt delivery remains available only when the user explicitly asks for it.

Alternatives considered:

- Broadcast a kickoff message to every participant.
  This would weaken the master-owned supervision model and make the start boundary less clear.
- Keep the compact start trigger but still require `accepted` / `rejected`.
  This would preserve the extra handshake without preserving much value, because readiness is already established by `initialize`.
- Use direct prompt as the ordinary default.
  This would make the start transport inconsistent with the mailbox-first in-loop contract and with the user's requested behavior.

### Decision: Routing packets remain authored structure, but initialize materializes their local slices into memo content

The authored plan can still carry routing packets and other dispatch structure, but v3 runtime recipients should consume memo material derived from that structure rather than depending on a separate start-charter page. The designated master's memo will carry the orchestration contract, and each participant memo will carry the local slice that participant needs.

Alternatives considered:

- Drop routing packets entirely and rely on freeform memo prose.
  This would simplify authoring wording but would lose the explicit dispatch structure that protects against runtime topology drift.
- Ask runtime agents to re-derive local slices from the full plan.
  This would reintroduce runtime recomputation and make the simplified start flow less reliable.

### Decision: Pairwise-v3 requires email/mailbox support for every required participant

Pairwise-v3 already treats email/mailbox as the default in-loop job communication channel. This change makes that dependency explicit and fail-closed: `initialize` and `recover_and_continue` must verify that the designated master and every required participant can participate in Houmao email/mailbox workflows. If any required participant lacks that support, the run does not become `ready` and ordinary `start` or recovery continuation must not proceed.

When `recover_and_continue` rebinds participants, it should also re-enable agents' email-notification posture where that posture was part of the run and the rebound participant exposes the supported gateway and mailbox surfaces.

Alternatives considered:

- Allow a partial fallback for agents without email.
  This would undercut the explicit pairwise-v3 communication contract and create a second runtime lane the plan did not authorize.

### Decision: Keep recovery semantics intentionally conservative for now

This change focuses on `initialize` and ordinary `start`. Recovery references should be updated so they no longer assume a start-charter page exists for v3, but `recover_and_continue` does not need to be fully redesigned in this proposal. If a later revision wants memo-first continuation without explicit acceptance, that can be handled as a follow-up change.

Alternatives considered:

- Couple this change with a full recover-and-continue redesign.
  That would broaden scope and slow down delivery of the initialize/start simplification the user actually asked for.

## Risks / Trade-offs

- [Memo blocks become too large or too repetitive] -> Keep master memo rich but normalize worker memo content to local slices and references instead of repeating the full plan everywhere.
- [Existing docs and operator habits still expect `accepted` / `rejected` from start] -> Update skill guidance, templates, and loop-authoring docs together so the new contract is presented consistently.
- [Recovery references still assume start-charter pages] -> Update recovery-facing references enough to store memo-slot references or otherwise avoid depending on removed v3 start-charter material.
- [The start trigger becomes too weak to diagnose bad initialization] -> Keep `initialize` as the hard readiness boundary and require it to finish memo materialization before `start` can fire.
- [Operators discover missing mailbox capability only after kickoff] -> Make email/mailbox verification an explicit `initialize` blocker before the run can reach `ready`.

## Migration Plan

1. Update the v3 OpenSpec capability to define memo-first initialize and lightweight start.
2. Revise v3 skill assets, templates, and docs so they no longer describe `start-charter` pages or start-time `accepted` / `rejected` replies for ordinary start.
3. Adjust any recovery-facing text or bookkeeping references that still assume v3 start-charter pages.
4. Verify docs and packaged skill references are coherent before archiving the change.

Rollback is straightforward because this is documentation-and-skill-contract work in an unstable system: revert the v3 asset and spec changes if the simplified model proves insufficient.

## Open Questions

- Should pairwise-v3 keep an explicit `ready` state, or collapse directly from `initializing` to `running` once start fires?
- Should v3 recovery store explicit memo-slot references in the runtime recovery record, or is it enough to reconstruct memo targets from the plan plus participant identity?
- Do we want a dedicated memo slot name for v3 initialize material, or should the change preserve the existing run-id-plus-slot sentinel structure with a renamed slot?
