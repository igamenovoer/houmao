## Context

The workspace-manager skill was refactored to expose a concise operation set: `plan`, `create`, `validate`, and `summarize`, with `execute` retained only as a compatibility alias for `create`. Its in-repo flavor now treats `<repo-root>/houmao-ws` as untracked local workspace state with task-local `shared-kb/`, task-owner `owner-states/<subdir>/...`, per-agent `states/`, and per-agent `repo/` worktrees.

The loop skills sit downstream of that contract. `houmao-agent-loop-pro` has a dedicated `prepare-workspace` execution page and generated workspace contract guidance that currently still mentions `execute`, older task/per-agent bookkeeping examples, and generic knowledge paths. `houmao-agent-loop-lite` has a smaller platform-boundary line that routes workspace planning or creation to the workspace manager.

The dependency direction should remain one-way:

```text
loop-pro / loop-lite
        |
        v
houmao-utils-workspace-mgr
```

The workspace manager must stay independent and consumer-neutral. Loop skills can depend on workspace-manager operation names and summaries, but workspace-manager guidance should not become loop-specific.

## Goals / Non-Goals

**Goals:**

- Align loop-pro `prepare-workspace` with workspace-manager `plan`, `create`, `validate`, and `summarize`.
- Treat `execute` only as legacy input accepted by loop-pro when reading older generated material or older operator wording.
- Update pro generated workspace contract guidance to use the untracked in-repo workspace surfaces: `shared-kb/`, `owner-states/<subdir>/...`, and per-agent `states/`.
- Add project-scope validation command inputs to pro workspace contracts so `prepare-workspace` can route them to workspace-manager `validate`.
- Update pro validation guidance so generated contracts distinguish planned, created, validated, summarized, missing, and manual/custom workspace evidence.
- Update lite platform-boundary guidance to include workspace-manager validation and summaries.
- Guard the alignment with packaged asset tests.

**Non-Goals:**

- Do not make `houmao-utils-workspace-mgr` reference loop-pro or lite.
- Do not change runtime Python APIs, CLI commands, or generated harness behavior.
- Do not implement actual workspace creation or validation logic in loop-pro or lite.
- Do not migrate existing user-generated loop directories automatically.
- Do not remove the `execute` compatibility alias from workspace-manager guidance during this change.

## Decisions

1. Keep `prepare-workspace` as the loop-pro adapter.

   `prepare-workspace` already consumes generated workspace contracts, prepared agent/profile facts, and manual evidence. It should remain the only pro page that adapts loop-local contracts into workspace-manager calls. General execution pages, generated role skills, and `prepare-agents` should not create worktrees or run workspace-manager operations directly.

   Alternative considered: let generated operator-control or role skills invoke workspace-manager directly. That would scatter platform setup across generated behavior and weaken the existing execution-stage boundary.

2. Model loop-pro workspace-manager operation as `plan | create | validate | summarize`.

   `plan` remains the default when the operator has not approved mutation. `create` is the standard mutating setup path. `validate` is the readiness check that can run project-scope commands. `summarize` gives compact facts that `validate-loop`, launch guidance, or operators can consume. `execute` may be accepted as stale generated wording but should be normalized to `create` in reports.

   Alternative considered: keep `execute` in loop-pro because workspace-manager still supports it as an alias. That preserves stale vocabulary in the downstream contract and makes validation look like a custom verification path rather than a first-class workspace-manager operation.

3. Represent loop run bookkeeping through workspace-manager surfaces.

   For standard in-repo workspaces, loop-pro should not keep asking for arbitrary task `runs/`, task `artifacts/`, per-agent `artifacts/`, and ignored `tmp/` directories as if the workspace root were tracked collaboration state. The standard surfaces are:

   - `shared-kb/` for cross-run task knowledge that may be shared across runs.
   - `owner-states/<subdir>/...` for task-owner per-run bookkeeping, reports, run evidence, and coordination records.
   - `<agent-name>/states/` for agent-local bookkeeping and scratch state.

   Rich artifacts that must become repository documentation should be intentionally copied or curated into tracked project files, not treated as automatic workspace-manager tracked output.

   Alternative considered: map every old loop artifact path into a new custom workspace directory. That keeps old examples intact but blurs the standard workspace-manager contract and risks making untracked workspace state look like a Git merge surface.

4. Treat project readiness as workspace-manager validation input.

   Pro workspace contracts should name explicit validation commands or safe documented project commands when the loop needs readiness evidence. `prepare-workspace` should pass those through to workspace-manager `validate` rather than inventing commands locally. If no safe command is supplied, the loop should record candidate tooling and ask for the validation command instead of manufacturing heavy builds.

   Alternative considered: keep pro `git-worktree-readiness.md` as the complete readiness algorithm. That would duplicate workspace-manager validation and drift again as workspace-manager evolves.

5. Keep lite minimal.

   Lite has no pro TOML workspace contract machinery. It only needs its platform boundary to say explicit workspace setup routes through workspace-manager planning, creation, validation, or summaries. Optional `execplan/specs/workspace.md` can continue to exist only when the selected lite process needs it.

## Risks / Trade-offs

- Existing generated pro material may say `execute` → Treat `execute` as legacy input and normalize it to `create` in new reports.
- Loop-pro examples may lose familiar `runs/` and `artifacts/` workspace paths → Reframe those as run artifacts under the loop directory or owner/agent state under the workspace, depending on whether they are loop-package artifacts or workspace-local bookkeeping.
- `git-worktree-readiness.md` overlaps workspace-manager validation → Narrow it into loop-facing readiness evidence guidance and route project command execution to workspace-manager `validate`.
- Lite may appear under-specified compared with pro → Keep lite intentionally small; only add a platform-boundary requirement unless later work adds a lite workspace contract format.
