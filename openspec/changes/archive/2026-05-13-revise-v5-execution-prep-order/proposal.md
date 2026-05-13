## Why

The current execution guidance puts workspace preparation before agent preparation, but managed workspace setup needs concrete agent and launch-profile names resolved first. The loop skill also lacks a dedicated execution-readiness validation step, so readiness concerns are split awkwardly between authoring validation, preparation pages, and `start`.

## What Changes

- Revise the normal execution order to:
  - `prepare-agents`
  - `prepare-workspace`
  - `validate-loop`
  - `start`
- Add `validate-loop` as the execution-time readiness validation subcommand.
- Keep `validate-execplan` scoped to generated artifact and contract validation.
- Revise `prepare-agents` so it prepares concrete agent/profile identities, prompt/profile material, skill bindings, support-skill requirements, notifier prompt posture, and memo posture before workspace setup.
- Revise `prepare-workspace` so it consumes concrete agent/profile facts from `prepare-agents` plus generated workspace contracts before routing supported layouts through `houmao-utils-workspace-mgr`.
- Move final readiness blocking for workspace, agents, mailbox/gateway/notifier, harness, run artifacts, and no in-chat waiting into `validate-loop`.
- Preserve the rule that `prepare-agents` and `prepare-workspace` are separate operator-invoked stages and do not call each other.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v5-skill`: Execution-stage behavior changes to put agent preparation before workspace preparation and add `validate-loop` as the dedicated execution-readiness gate before `start`.

## Impact

- Affected skill assets: `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/`.
- Affected execution routing: add `validate-loop`; reorder execution-stage guidance.
- Affected execution pages: revise `prepare-agents`, `prepare-workspace`, and `start`; add `validate-loop`.
- Affected validation guidance: keep `validate-execplan` authoring-focused and move runtime readiness checks to `validate-loop`.
- Affected developer design docs: update execution-stage rationale so future revisions preserve the corrected order.
