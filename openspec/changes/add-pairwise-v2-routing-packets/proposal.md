## Why

The current `houmao-agent-loop-pairwise-v2` preparation model still centers on a separate operator-origin preparation mail wave before the master trigger. For simple or long-running pairwise plans, that adds extra prestart traffic and can drift out of the active context once agents rely on old preparation mail instead of the current edge handoff.

## What Changes

- Make plan-time routing packets the default v2 preparation strategy for authored pairwise loop plans.
- Precompute subtree slices during authoring so runtime intermediate agents do not need to perform graph reasoning when delegating to descendants.
- Require each non-leaf participant to receive a local dispatch table and exact child packet text to append to downstream pairwise edge handoffs.
- Preserve the existing operator-origin preparation wave as an explicit opt-in strategy for complex plans, acknowledgement-gated preflight, or user-requested warmup of participants.
- Update v2 initialize/start guidance, plan structure, templates, run-charter guidance, and the v2 OpenSpec requirement so `ready` can mean either routing packets are prepared or an explicit operator preparation wave has completed, depending on the chosen strategy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v2-skill`: change the default prestart strategy from sending operator-origin preparation mail to delegating participants to using plan-time precomputed routing packets, while keeping the current targeted preparation wave as an explicit opt-in mode.

## Impact

- Affected assets:
  - `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v2/`
  - `openspec/specs/houmao-agent-loop-pairwise-v2-skill/spec.md`
- No new runtime loop engine, mailbox transport, or gateway API is introduced.
- Existing v2 lifecycle verbs remain available, but `initialize` and `start` semantics change for the default prestart path.
