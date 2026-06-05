# Agent Loop Git Worktree Workspaces Are Created but Not Enforced

## Status

Known issue as of 2026-06-04. Observed in a `houmao-agent-loop-pro` generated loop that used `houmao-utils-workspace-mgr` to prepare per-agent Git worktrees.

## Summary

`houmao-agent-loop-pro` can generate a loop contract that requests isolated per-agent Git worktrees, and `houmao-utils-workspace-mgr` can successfully create those worktrees. The generated agent bindings and launch/runtime posture can still launch all agents from the parent repo root, so agents write source changes into the shared checkout instead of their private worktrees.

This breaks the main safety property of multi-agent coding workspaces: source-editing agents should produce owned, reviewable changes in separate worktree branches. In the observed run, the private worktrees stayed clean while the parent checkout accumulated candidate code and variant registry edits.

## Affected Components

- `houmao-agent-loop-pro`: generated workspace contracts, generated agent bindings, `prepare-agents`, `validate-loop`, and `launch-agents` posture.
- `houmao-utils-workspace-mgr`: workspace creation, workspace summary, launch-profile cwd preparation, and validation coverage.
- Managed-agent runtime launch: runtime manifests preserved `working_directory` as the parent repo root, even for source-mutating coding agents.

## Observed Evidence

The issue was observed in `/data/ssd1/huangzhe/code/hmdemo-mlsys26-contest` during the generated loop `teams/lead-code-synth-research`.

- Private worktrees existed under `houmao-ws/lead-code-synth-research/<agent>/repo` for `lcsr-planner`, `lcsr-cuda-coder-1`, `lcsr-cuda-coder-2`, `lcsr-synthesizer`, `lcsr-researcher`, and `lcsr-evaluator`.
- `git -C houmao-ws/lead-code-synth-research/<agent>/repo status --short` returned zero entries for all six private worktrees after the run.
- The parent checkout had source and candidate changes, including `configs/variants.toml`, `solution/cuda/kernel.cu`, and many untracked `variants/cuda/c1-*` and `variants/cuda/c2-*` directories.
- The generated workspace contract contained a contradiction: `teams/lead-code-synth-research/execplan/specs/workspace/workspace.toml` set `source_mutation_rule = "agents edit source only inside their own private repo/ Git worktree"`, but also set `launch_cwd_policy = "repo-root"` and `launch_cwd = "<repo-root>"`.
- The generated agent bindings repeated the root launch posture: `teams/lead-code-synth-research/execplan/agents/bindings.toml` set `launch_cwd_policy = "repo-root"` for every `lcsr-*` agent.
- Runtime manifests confirmed the actual launch cwd. For example, `.houmao/runtime/sessions/local_interactive/local_interactive-20260604-050309Z-704cfcd0/manifest.json` for `lcsr-cuda-coder-1` recorded `working_directory = "/data/ssd1/huangzhe/code/hmdemo-mlsys26-contest"`, and `.houmao/runtime/sessions/local_interactive/local_interactive-20260604-050314Z-3ff4b2d9/manifest.json` recorded the same parent checkout for `lcsr-cuda-coder-2`.

## Expected Behavior

When a generated loop selects per-agent Git worktrees and marks source mutation as private-worktree-only, each source-mutating agent should launch with `cwd` equal to its own `worktree_path`. The parent checkout can remain a shared read surface, but source edits should not land there unless the loop explicitly chooses shared-root editing.

`validate-loop` should fail when the generated workspace contract requires private worktrees but prepared launch profiles or live session facts still point source-mutating agents at the parent repo root.

## Actual Behavior

The workspace manager prepared the worktree topology, but the generated launch posture left agents in the parent repo root. The runtime honored the launch cwd, and the prompts alone were not strong enough to enforce worktree use. Source edits landed in the shared parent checkout.

## Impact

- Parallel coder changes lose branch ownership because they accumulate in the parent checkout.
- Review and synthesis become harder because root working-tree state mixes all agent outputs.
- The operator may believe worktree isolation is active because the worktrees exist and validation passes.
- Future relaunches can start from a contaminated parent checkout instead of clean per-agent branches.

## Proposed Fix

1. In `houmao-agent-loop-pro`, when the generated workspace contract requires per-agent Git worktrees, derive each binding's launch cwd from that agent's `worktree_path` by default for any source-mutating participant.
2. In `houmao-utils-workspace-mgr`, have `create` emit or update launch-profile cwd facts for each prepared profile, or explicitly report that launch cwd was not enforced.
3. In `validate-loop`, add a hard check that compares generated source-mutation policy, prepared workspace facts, launch profiles, and live/runtime manifest `working_directory` values when agents are already launched.
4. In `launch-agents`, start each agent from the prepared per-agent cwd instead of the parent repo root when workspace facts require a private worktree.
5. Keep prompt and memo guidance as a secondary guard by including the absolute private worktree path and instructing agents to verify `pwd` before source edits.

## Regression Test Ideas

- Generate a loop with two source-mutating coder agents and required in-repo Git worktrees, then assert generated bindings use distinct worktree cwd values.
- Run workspace validation after profile preparation and assert failure when `source_mutation_rule` requires private worktrees but `launch_cwd_policy = "repo-root"`.
- Launch a dry-run managed agent from a prepared profile and assert the runtime manifest `working_directory` equals the expected private worktree path.
- Add a negative test that allows `repo-root` only when the loop explicitly chooses shared-root editing and records that policy.

## Workaround

Before relaunching a worktree-backed loop, manually update the launch profiles or launch command inputs so source-mutating agents start in `houmao-ws/<task>/<agent>/repo`. Then inspect the runtime manifest after launch and verify `working_directory` before enabling mail notifiers.
