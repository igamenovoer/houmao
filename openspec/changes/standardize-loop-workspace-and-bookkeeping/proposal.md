## Why

Loop-planned agents already have strong control-plane guidance, but they do not yet carry a deterministic contract for where participants are allowed to work or how operator-visible bookkeeping should be maintained. In practice that leaves loop runs inconsistent across teams and sessions, especially when Houmao already has a separate workspace-management surface with explicit in-repo and out-of-repo postures.

## What Changes

- Add a standard loop-run contract that separates workspace posture from bookkeeping posture and makes both explicit in authored loop plans.
- Add a built-in standard workspace mode for loop plans that reuses the existing `houmao-utils-workspace-mgr` in-repo and out-of-repo styles instead of inventing a separate loop-only layout.
- Define standard workspace rules for loop-planned runs, including where code edits happen, whether repo-root or workspace-root visibility surfaces are writable, whether ad hoc worktrees are allowed, and which shared surfaces are read-only versus writable.
- Define standard bookkeeping rules for loop-planned runs as semantic obligations rather than a fixed directory tree: expected bookkeeping categories, visibility and ownership expectations, update moments, and explicit plan-declared file locations.
- Require bookkeeping locations to be declared by the user-authored plan or charter rather than imposing a Houmao-owned fixed subtree under per-agent `kb/`.
- Integrate the loop skills with the workspace-manager skill so a loop plan can reference or request a prepared standard workspace posture instead of improvising one during run setup.
- Update loop-plan templates, reporting guidance, and loop-authoring docs so operators can see the workspace contract and bookkeeping contract up front.

## Capabilities

### New Capabilities

- `loop-run-contracts`: defines the standard loop workspace and bookkeeping contract vocabulary, including standard versus custom postures, integration with prepared in-repo or out-of-repo workspaces, and the rule that bookkeeping locations are explicit plan-owned paths rather than a fixed Houmao subtree.

### Modified Capabilities

- `houmao-agent-loop-pairwise-skill`: add workspace-contract and bookkeeping-contract requirements to stable pairwise authoring and run-control guidance.
- `houmao-agent-loop-pairwise-v2-skill`: add workspace-contract and bookkeeping-contract requirements to enriched pairwise authoring, initialize, start, and reporting guidance.
- `houmao-agent-loop-generic-skill`: add workspace-contract and bookkeeping-contract requirements to generic loop authoring and run-control guidance.
- `houmao-utils-workspace-mgr-skill`: add requirements for loop-facing standard workspace posture summaries that loop plans can reference without redefining in-repo or out-of-repo semantics.
- `docs-loop-authoring-guide`: document the standard workspace and bookkeeping contract model for loop plans and explain when users should keep the standard mode versus declare a custom contract.

## Impact

- Packaged loop skill assets under `src/houmao/agents/assets/system_skills/` for `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-generic`.
- Packaged workspace-manager skill assets under `src/houmao/agents/assets/system_skills/houmao-utils-workspace-mgr/`.
- OpenSpec specs for the loop skills, workspace-manager skill, loop authoring docs, and the new cross-cutting `loop-run-contracts` capability.
- Loop-plan templates, references, and examples that currently describe reporting but not a first-class workspace or bookkeeping contract.
- No runtime engine change is required for the first step. This is primarily a contract, guidance, and documentation change for how loop-planned runs are authored and interpreted.
