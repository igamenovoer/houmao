## Context

Houmao currently splits pairwise loop work across two packaged skills:

- `houmao-loop-planner` owns the richer operator-facing authoring, distribution, and handoff bundle,
- `houmao-agent-loop-pairwise` owns pairwise-specific planning plus live `start`, `status`, and `stop`.

That split is now at odds with the desired pairwise workflow. The pairwise run should have one loop-kind-specific entrypoint that owns authoring, participant preparation, and live run control together. The repository already has the lower-level behavior needed for the runtime side:

- the pairwise edge-loop pattern already defines non-blocking downstream dispatch, mailbox-first review, and reminder-driven supervision,
- gateway mail-notifier control already exists,
- `houmao-agent-inspect` now exists as the canonical read-only skill for peeking at managed-agent state when mailbox review is insufficient,
- the reserved operator mailbox `HOUMAO-operator@houmao.localhost` already exists,
- operator-origin mailbox delivery currently remains one-way and rejects replies explicitly.

The requested change therefore combines a packaged-skill boundary change with a mailbox contract change:

- remove `houmao-loop-planner` after its pairwise-relevant authoring material is absorbed,
- expand `houmao-agent-loop-pairwise` to own pairwise authoring, prestart preparation, and run control,
- evolve operator-origin mailbox delivery from one fixed no-reply posture into explicit reply-policy modes so preparation mail can optionally collect readiness acknowledgements.

Constraints:

- pairwise execution must still compose the existing pairwise edge-loop pattern rather than introduce a new runtime engine,
- participant preparation must be standalone and must not depend on hidden assumptions about which upstream participant may later contact the agent,
- downstream dispatch must still end the current live turn rather than block in chat,
- reply-enabled operator-origin mail must preserve explicit provenance and a real reserved system sender,
- relay loop authoring remains out of scope for this design except for migration away from the removed generic planner skill.

## Goals / Non-Goals

**Goals:**

- Make `houmao-agent-loop-pairwise` the single packaged entrypoint for pairwise authoring, prestart preparation, and run control.
- Preserve the existing pairwise distinction between control plane and execution plane.
- Define pairwise preparation artifacts that are standalone for each participant and compatible with either default fire-and-proceed start or optional acknowledgement-gated start.
- Require prestart to verify or enable gateway mail notification before run activation and to dispatch preparation email to all participants before the master trigger.
- Add an authored optional downstream timeout-watch policy that uses reminder-driven, mailbox-first follow-up plus `houmao-agent-inspect`.
- Extend operator-origin mailbox semantics so preparation mail can be reply-disabled by default or reply-enabled to the reserved operator mailbox when acknowledgement mode is requested.

**Non-Goals:**

- Do not introduce a new generic loop runtime engine or scheduler.
- Do not keep `houmao-loop-planner` as a deprecated compatibility layer.
- Do not redesign relay-loop runtime semantics.
- Do not turn operator-origin mail into a general human inbox feature beyond the reserved operator mailbox account and explicit reply-policy modes.
- Do not wait inside the same live provider turn for downstream work or acknowledgement mail.

## Decisions

### Decision: Remove `houmao-loop-planner` and use loop-kind-specific authoring skills directly

The change will not keep a generic planner skill. Instead:

- pairwise authoring and pairwise prestart preparation move into `houmao-agent-loop-pairwise`,
- relay users migrate directly to `houmao-agent-loop-relay` for relay-specific authoring and run control,
- `houmao-loop-planner` skill assets, tests, and spec requirements are removed in the same change rather than deprecated first.

Why:

- the new preparation and activation contract is pairwise-specific,
- keeping two pairwise authoring entrypoints would preserve the current boundary confusion,
- the repository already has loop-kind-specific runtime skills, so loop-kind-specific authoring is a cleaner steady state.

Alternative considered:

- keep `houmao-loop-planner` as a deprecated compatibility skill that delegates into the pairwise or relay skills. Rejected because it would preserve overlapping ownership during the exact phase where the workflow needs to become clearer.

### Decision: Keep pairwise single-file and bundle forms, but reshape bundle contents around prestart

`houmao-agent-loop-pairwise` should keep its existing two-form authoring model:

- a single-file plan for small runs,
- a bundle rooted at `plan.md` for larger runs.

The bundle form should absorb the useful pairwise-specific planning material from `houmao-loop-planner`, but not copy its old file set verbatim. For pairwise runs, the authored bundle should center on:

- `plan.md` as the canonical operator/master view,
- `prestart.md` for notifier, preparation-mail, acknowledgement, and master-trigger procedure,
- `agents/<participant>.md` for standalone participant preparation briefs,
- optional support files such as `reporting.md`, `delegation.md`, `scripts/README.md`, and scripts.

Why:

- the current pairwise skill already supports compact single-file and structured bundle forms,
- the old `participants.md` and `distribution.md` shapes encode operator-facing and upstream-aware assumptions that do not fit the new standalone preparation requirement,
- pairwise prestart procedure is now first-class authored content and deserves an explicit artifact.

Alternative considered:

- adopt the old planner bundle shape wholesale with `participants.md`, `execution.md`, and `distribution.md`. Rejected because those files were designed around operator distribution and participant sections that explicitly say who each agent receives work from, which conflicts with the new standalone preparation posture.

### Decision: Standalone participant preparation briefs replace upstream-aware participant packets

For pairwise runs, each participant should receive a preparation brief that is usable on its own before the run starts. The brief must tell the participant:

- its role,
- the resources or artifacts available to it,
- which agents it may delegate to,
- any delegation rules by work category when relevant,
- mailbox, reminder, receipt, or result obligations,
- forbidden actions.

The brief must not assume the participant already knows what upstream peer will contact it later or what exact upstream message shape will arrive during preparation.

Why:

- this is the core user requirement for the new preparation stage,
- upstream relationships belong to the authored run topology, not to each participant’s initial preparation context,
- a standalone brief is easier to reuse in both fire-and-proceed and acknowledgement-gated start modes.

Alternative considered:

- keep one global participant sheet and let the operator extract relevant pieces manually. Rejected because it pushes the most important preparation boundary back into operator interpretation rather than authored contract.

### Decision: `start` becomes a two-stage procedure: preparation wave first, master trigger second

The pairwise operating model will keep `start`, `status`, and `stop`, but `start` becomes explicitly two-stage:

1. preflight and preparation wave,
2. master trigger.

The preflight and preparation wave should do all of the following before the master trigger:

- verify the participant set and authored preparation material,
- verify or enable gateway mail-notifier behavior for participating agents,
- send one preparation email to every participant, including the designated master,
- optionally wait for acknowledgement replies when the authored or user-selected policy requires them.

Only after the preparation wave is dispatched, and after acknowledgement gating if enabled, should the operator send the normalized start charter to the master.

Why:

- the run should not begin before participants receive the preparation context that explains their allowed delegation resources and local obligations,
- notifier enablement is part of readiness for this workflow and should not remain implicit,
- separating preparation mail from the master trigger preserves the existing control-plane/execution-plane boundary.

Alternative considered:

- treat preparation as an optional side effect of the master start request. Rejected because it would hide prestart dependencies inside the master behavior and blur whether other participants were actually prepared before the run began.

### Decision: Support two explicit preparation acknowledgement modes

Pairwise prestart should support exactly two authored postures:

- default fire-and-proceed mode: dispatch preparation mail and continue without waiting for replies,
- acknowledgement-gated mode: dispatch preparation mail that instructs participants to reply and hold the master trigger until the required replies arrive or a blocking condition is surfaced.

The default remains non-blocking to match the requested operator workflow. Acknowledgement gating is opt-in rather than implicit.

Why:

- some runs only need preparation context distributed; they do not need a readiness handshake,
- other runs need an explicit readiness barrier before the master begins dispatch,
- keeping both modes inside the authored prestart contract avoids out-of-band procedural differences.

Alternative considered:

- always require acknowledgement replies. Rejected because it would turn the default operator flow into a blocking workflow that the user explicitly does not want.

### Decision: Extend operator-origin mail with explicit reply-policy modes

Operator-origin mail currently uses reserved sender provenance and an explicit no-reply posture. This change should keep the reserved sender and explicit provenance, but replace the fixed one-way rule with explicit reply-policy modes:

- `none`: current behavior; replies reject explicitly,
- `operator_mailbox`: replies are allowed and target `HOUMAO-operator@houmao.localhost`.

Preparation mail in default mode should use `reply_policy = none`. Preparation mail in acknowledgement-gated mode should use `reply_policy = operator_mailbox`.

Implementation implications:

- the protocol layer keeps the `x-houmao-origin` marker,
- the reply-policy header becomes authoritative behavior rather than documentation-only metadata,
- reply-enabled operator-origin messages must still be distinguishable from ordinary mailbox participation,
- filesystem transport remains the only supported operator-origin transport in v1.

Why:

- the repository already has the reserved operator mailbox account, so acknowledgement threads should land in a maintained system mailbox rather than in a hidden new channel,
- using explicit reply policy is cleaner than switching prep mail from operator-origin `post` to ordinary `send`,
- the default no-reply posture remains intact for all existing one-way operator-origin uses.

Alternative considered:

- instruct participants to send a fresh message to a system address rather than replying to the preparation thread. Rejected because it loses the shared thread/correlation shape and creates two different preparation-mail semantics instead of one explicit reply-policy contract.

### Decision: Timeout watch remains reminder-driven, mailbox-first, and opt-in

The optional downstream timeout-watch mechanism should extend the existing pairwise supervision model rather than replace it.

For selected participants or delegation edges, the authored plan may define a timeout-watch policy that requires the acting participant to:

- persist local due-state in the loop ledger,
- end the current live turn after downstream dispatch,
- later reopen the ledger through a reminder-driven review round,
- check mailbox first for receipts, results, or acknowledgements,
- inspect downstream state through `houmao-agent-inspect` only when the expected downstream signal is overdue.

The guidance should continue to prefer one supervisor reminder per agent rather than one reminder per active edge by default.

Why:

- the existing pairwise pattern already encodes the right non-blocking and mailbox-first supervision posture,
- `houmao-agent-inspect` already centralizes the supported read-only inspection ladder and is the right seam for downstream peeking,
- timeout watch is an optional escalation path, not a new execution model,
- read-only inspection belongs in a later review round, not in the same turn that sent downstream work.

Alternative considered:

- perform immediate downstream inspection in the same turn that sends the request. Rejected because it violates the current pairwise pattern and the requested non-blocking chat-turn boundary.

## Risks / Trade-offs

- [Removing `houmao-loop-planner` breaks explicit planner invocations] -> Update skill overview docs, routing guidance, and tests in the same change so pairwise and relay users have direct migration targets immediately.
- [Reply-enabled operator-origin mail broadens a previously one-way contract] -> Keep `reply_policy = none` as the default, require explicit reply policy metadata on every operator-origin message, and limit reply-enabled behavior to the reserved operator mailbox account.
- [Notifier enablement can fail during preflight] -> Treat notifier setup as explicit readiness work and surface blocked start conditions clearly before the master trigger is sent.
- [Acknowledgement-gated start can create waiting state and operator overhead] -> Keep acknowledgement gating opt-in and continue to allow fire-and-proceed as the default authored posture.
- [Pairwise bundle contents may drift if both single-file and bundle forms remain supported] -> Keep `plan.md` as the canonical entrypoint, require clearly separable participant preparation sections in single-file form, and reserve richer per-agent files for bundle form.

## Migration Plan

1. Expand the `houmao-agent-loop-pairwise` capability and packaged skill assets so pairwise authoring includes standalone participant preparation material, prestart procedure, and updated start guidance.
2. Extend operator-origin mailbox protocol, gateway mailbox handling, and mailbox-facing CLI/server surfaces to honor explicit reply-policy modes while preserving default no-reply behavior.
3. Update pairwise docs and tests to cover notifier preflight, preparation wave ordering, acknowledgement-gated mode, and optional timeout-watch policy.
4. Remove `houmao-loop-planner` skill assets, related tests, and spec requirements once the pairwise replacement path is in place.
5. Update any docs or routing references that still tell pairwise users to go through `houmao-loop-planner`.

Rollback is straightforward:

- restore the removed planner skill assets and references,
- revert pairwise skill guidance to its earlier plan-plus-run-control scope,
- restore operator-origin reply policy to fixed no-reply behavior.

## Open Questions

- None for proposal scope. This design fixes the default preparation posture as fire-and-proceed, makes acknowledgement gating opt-in, keeps timeout watch optional, and keeps reply-enabled operator-origin mail limited to the reserved operator mailbox account.
