## Why

Pairwise loop authoring is currently split between `houmao-loop-planner` and `houmao-agent-loop-pairwise`, while the live start workflow still leaves pre-start participant preparation, notifier enablement, and late downstream inspection insufficiently integrated with the pairwise authoring contract. Houmao needs one pairwise entrypoint that owns the pairwise authoring contract end to end and one supported prestart model that prepares every participant before the master is triggered without forcing the operator to block on acknowledgements by default.

## What Changes

- **BREAKING** Merge pairwise bundle authoring and pairwise runtime handoff into `houmao-agent-loop-pairwise`, then remove the packaged `houmao-loop-planner` system skill and its pairwise routing role.
- Expand `houmao-agent-loop-pairwise` so it owns pairwise authoring, standalone per-agent preparation guidance, prestart preparation flow, and run control.
- Replace pairwise use of operator-facing `participants.md` and `distribution.md` with pairwise artifacts that support per-agent standalone preparation briefs and explicit prestart procedure.
- Require pairwise prestart to verify or enable gateway mail notification for participating agents before the run starts and to send a preparation email to every participant before the master receives the start trigger.
- Support two preparation modes:
- default fire-and-proceed mode where the operator sends preparation mail and continues without waiting for readiness acknowledgements,
- optional acknowledgement mode where preparation mail instructs participants to reply to the reserved Houmao operator mailbox and the operator may wait for those readiness replies before triggering the master.
- Require the master trigger to remain a separate control-plane message sent only after the preparation wave is dispatched.
- Add optional downstream timeout-watch policy for selected agents so overdue downstream work is reviewed later through reminder-driven mailbox-first supervision plus `houmao-agent-inspect`, without waiting inside the same live chat turn that sent the downstream request.
- Extend operator-origin mailbox delivery so operator-origin preparation mail can remain one-way by default but can optionally allow replies back to the reserved operator mailbox when the authored pairwise prestart policy requires readiness acknowledgement.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-skill`: expand the skill from pairwise plan plus run control into full pairwise authoring, prestart preparation, optional readiness acknowledgement, and optional downstream timeout-watch policy.
- `houmao-loop-planner-skill`: remove the packaged planner skill after pairwise authoring and handoff responsibilities move into `houmao-agent-loop-pairwise`.
- `agent-mailbox-operator-origin-send`: change operator-origin mailbox semantics from always-no-reply to explicit reply-policy modes so pairwise preparation mail can optionally accept readiness replies into `HOUMAO-operator@houmao.localhost`.

## Impact

- Affected skill assets under `src/houmao/agents/assets/system_skills/`, especially `houmao-agent-loop-pairwise` and removal of `houmao-loop-planner`
- Cross-skill composition with existing Houmao-owned skills, especially `houmao-agent-inspect` for read-only downstream peeking during timeout-watch follow-up
- Affected mailbox transport and gateway mailbox behavior for operator-origin reply policy handling
- Affected system-skill packaging, mailbox, and runtime behavior tests under `tests/unit/` and relevant integration coverage for gateway/mailbox flows
- Affected docs and skill references that currently describe pairwise handoff through `houmao-loop-planner`
