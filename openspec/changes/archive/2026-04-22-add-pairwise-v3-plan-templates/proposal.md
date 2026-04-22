## Why

Pairwise-v3 currently teaches authors to declare bookkeeping paths and reporting expectations, but it does not teach the planning agent to generate a plan-owned `templates/` bundle with reusable reporting and bookkeeping scaffolds. That leaves bundle plans without a durable source of task-shaped report forms, handoff outlines, or bookkeeping structures even when the run contract clearly needs them.

## What Changes

- Extend pairwise-v3 bundle-plan guidance to support a generated `<plan-output-dir>/templates/` directory as part of the authored plan bundle.
- Require the authoring flow to decide when task complexity or operator needs make reusable templates part of the plan contract.
- Teach pairwise-v3 to generate sensible reporting templates from the authored reporting contract, including canonical report surfaces such as peek, completion, recovery, stop, and hard-kill summaries when those surfaces are part of the run.
- Teach pairwise-v3 to generate sensible bookkeeping templates from the task objective, topology, participant responsibilities, and declared bookkeeping paths instead of inventing one fixed bookkeeping subtree.
- Clarify that plan-bundle templates are authored reusable source artifacts, while mutable run outputs belong in declared workspace or bookkeeping paths and runtime-owned recovery files remain outside both surfaces.
- Update loop-authoring documentation so pairwise-v3 users understand when bundle plans should carry templates and how those templates relate to workspace and bookkeeping posture.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v3-skill`: The skill requirements will change so bundle plans may include a generated `templates/` directory with task-shaped reporting and bookkeeping templates, with clear authored-plan versus mutable-run boundaries.

## Impact

- OpenSpec delta for `houmao-agent-loop-pairwise-v3-skill`
- Pairwise-v3 skill assets under `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v3/`
- Pairwise-v3 authoring references and bundle templates
- Pairwise-v3 user documentation in `docs/getting-started/loop-authoring.md`
