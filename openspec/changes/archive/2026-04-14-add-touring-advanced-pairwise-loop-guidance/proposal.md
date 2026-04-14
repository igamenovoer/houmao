## Why

`houmao-touring` already helps users branch across setup, launch, live operations, and lifecycle follow-up, but it does not expose the shipped pairwise loop-planning skills as an advanced tour path. Users who discover multi-agent loop creation during a tour need explicit guidance that points them to the stable and v2 pairwise loop skills without collapsing those manual-invocation-only skills into ordinary touring automation.

## What Changes

- Add an advanced-usage touring branch for agent-loop creation.
- Teach the touring skill to present `houmao-agent-loop-pairwise` as the stable pairwise loop planner and run-control surface for `plan`, `start`, `status`, and `stop`.
- Teach the touring skill to present `houmao-agent-loop-pairwise-v2` as the enriched pairwise loop planner for `plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `stop`, and `hard-kill`.
- Preserve the existing pairwise skill boundary: touring introduces and routes the branch, while the pairwise skills own composed loop planning, run-control details, and their manual-invocation rules.
- Keep elemental immediate driver-worker edge protocol guidance on `houmao-adv-usage-pattern`; touring should not restate that protocol inline.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-touring-skill`: Add advanced-usage tour guidance for pairwise agent-loop creation and route stable/v2 pairwise loop work to the maintained loop-planning skills.

## Impact

- Affected system-skill assets:
  - `src/houmao/agents/assets/system_skills/houmao-touring/SKILL.md`
  - likely a new `src/houmao/agents/assets/system_skills/houmao-touring/branches/advanced-usage.md`
- Affected tests:
  - system-skill installation/projection tests that assert touring branch files and key routing text
- No runtime CLI, mailbox, gateway, or loop-engine behavior changes.
