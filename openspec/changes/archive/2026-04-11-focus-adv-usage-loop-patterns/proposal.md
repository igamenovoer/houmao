## Why

The advanced-usage loop pattern docs currently mix elemental protocol guidance with larger graph composition guidance, which makes the basic pairwise and relay patterns harder to choose and apply correctly. The dedicated loop-planning skills now own composed run planning, so `houmao-adv-usage-pattern` should stay focused on the atomic patterns it is meant to compose.

## What Changes

- Narrow the pairwise edge-loop pattern to one driver, one worker, and one `edge_loop_id` for a single local-close round.
- Remove or redirect recursive child edge-loop and multi-edge graph-planning guidance from the elemental pairwise pattern page.
- Require pairwise driver follow-up to use read-only downstream peeking through `houmao-agent-inspect` before resending a due request, and to treat direct prompt/message status probes as a last resort when read-only inspection cannot determine whether the worker is still working on that `edge_loop_id`.
- Narrow the relay-loop pattern to one ordered N-node relay lane with one master/loop origin and one final egress returning the final result to that master.
- Remove or redirect multi-loop, fan-out, and graph-of-loops language from the elemental relay pattern page.
- Require relay upstream follow-up to use read-only downstream peeking through `houmao-agent-inspect` before resending a due handoff, and to treat direct prompt/message status probes as a last resort when read-only inspection cannot determine whether the downstream agent is still working on the same `loop_id` and `handoff_id`.
- Update the top-level advanced-usage chooser to distinguish atomic protocol pages from dedicated loop-planning/run-control skills.
- Preserve existing lower-level contracts for gateway handoff, mailbox receipts/results/acknowledgements, local `HOUMAO_JOB_DIR` ledgers, idempotent retry, status-aware follow-up, and timing policy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-adv-usage-pattern-skill`: change the packaged advanced-usage skill contract so pairwise and relay loop pages describe elemental patterns and route larger composed topologies to dedicated loop skills.

## Impact

- Affected spec: `openspec/specs/houmao-adv-usage-pattern-skill/spec.md`
- Affected skill assets: `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/SKILL.md`, `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/patterns/pairwise-edge-loop-via-gateway-and-mailbox.md`, and `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/patterns/relay-loop-via-gateway-and-mailbox.md`
- Affected validation surface: any system-skill asset or documentation tests that assert the current advanced-usage pattern wording
- No new gateway, mailbox, manager, or runtime API surface
