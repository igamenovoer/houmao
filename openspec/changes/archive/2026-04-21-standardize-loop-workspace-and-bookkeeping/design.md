## Context

Pairwise-v2 already owns rich pairwise lifecycle behavior: routing-packet prestart, durable managed-memory guidance, runtime-owned recovery records, and `recover_and_continue`. What it does not own is a first-class workspace contract. That leaves operators choosing between ad hoc workspace prose inside loop plans and a separate workspace-manager skill that currently knows nothing about a v2/v3 pairwise run contract.

The user requirement here is more precise than the earlier draft:

- pairwise-v3 should be the workspace-aware extension of pairwise-v2,
- pairwise-v3 should let the operator choose a standardized Houmao workspace or a custom operator-owned workspace,
- `houmao-utils-workspace-mgr` should remain standard-only rather than becoming a universal custom-workspace inspector,
- standard in-repo workspaces should be task-scoped under `houmao-ws/<task-name>/...`,
- runtime-owned recovery records must remain separate from user-authored bookkeeping and workspace notes.

That gives us a clear split of responsibility:

- `houmao-agent-loop-pairwise-v3` owns workspace contract choice inside the loop plan,
- `houmao-utils-workspace-mgr` owns only the standardized Houmao workspace layout,
- pairwise-v2 remains intact as the non-workspace-specialized predecessor.

## Goals / Non-Goals

**Goals:**

- Introduce `houmao-agent-loop-pairwise-v3` as the workspace-aware extension of v2.
- Let pairwise-v3 plans declare `workspace_contract.mode = standard | custom`.
- Define standard in-repo posture for pairwise-v3 as task-scoped under `houmao-ws/<task-name>/...`.
- Keep pairwise-v3 compatible with pairwise-v2 lifecycle ideas, including initialize/start/recovery boundaries.
- Keep `houmao-utils-workspace-mgr` standard-only and task-scoped for in-repo mode.
- Make docs and packaging reflect the new v2/v3 distinction clearly.

**Non-Goals:**

- Do not retrofit standard/custom workspace modes into `houmao-utils-workspace-mgr`.
- Do not redefine pairwise-v2 in place; v3 is additive.
- Do not redesign the out-of-repo workspace-manager flavor.
- Do not redefine Houmao runtime-owned recovery files as user-authored bookkeeping.
- Do not impose a fixed subtree under per-agent `kb/` for custom workspaces.

## Decisions

### Decision: Introduce pairwise-v3 instead of mutating pairwise-v2 in place

The workspace-aware loop contract should ship as `houmao-agent-loop-pairwise-v3`, not as a breaking rewrite of v2.

Why:

- v2 already has a stable mental model around initialize/start/recover-and-continue;
- workspace-aware planning is a meaningful extension, not just a small wording change;
- keeping v2 intact makes migration and docs comparison cleaner.

Alternative considered: modify pairwise-v2 directly. Rejected because it would blur whether old v2 plans are still valid and would mix workspace posture changes into an existing versioned surface.

### Decision: Standard/custom workspace choice belongs to pairwise-v3, not to workspace-manager

Pairwise-v3 will own a workspace contract such as:

```text
workspace_contract:
  mode: standard | custom
```

If `mode = standard`, pairwise-v3 uses Houmao's standard workspace posture and may refer to or require a workspace prepared through `houmao-utils-workspace-mgr`.

If `mode = custom`, pairwise-v3 records operator-provided paths and rules directly in the loop plan. In that case, `houmao-utils-workspace-mgr` is not invoked and does not gain any custom-workspace lane.

Why:

- the operator chooses workspace posture as part of the run contract;
- the workspace manager should stay focused on preparing Houmao-standard layouts;
- “custom workspace” is a loop-planning concern, not a workspace-manager concern.

Alternative considered: add `custom` mode to workspace-manager too. Rejected because it would turn the workspace manager into a generic workspace abstraction layer instead of a standard Houmao workspace preparer.

### Decision: Standard in-repo posture is task-scoped

The standard in-repo posture used by pairwise-v3 and prepared by workspace-manager should be:

```text
<repo-root>/
  houmao-ws/
    workspaces.md
    <task-name>/
      workspace.md
      shared-kb/
      <agent-name>/
        kb/
        repo/
```

This means:

- task root: `<repo-root>/houmao-ws/<task-name>`
- authoritative task contract: `<task-root>/workspace.md`
- task-local shared knowledge: `<task-root>/shared-kb/`
- repo-level index only: `<repo-root>/houmao-ws/workspaces.md`
- task-qualified branches such as `houmao/<task-name>/<agent-name>/main`

Why:

- multiple teams can coexist in one repository;
- common role names stop colliding;
- `shared-kb` and `workspace.md` become task-local rather than repo-global.

Alternative considered: keep the flat `houmao-ws/<agent-name>/...` shape. Rejected because it cannot represent multiple concurrent teams cleanly.

### Decision: Repo root can remain the shared visibility surface in standard in-repo mode

For standard in-repo posture, the launch cwd may still remain `<repo-root>`, while writes are task-local by default:

- source writes: `<task-root>/<agent-name>/repo`
- task notes: `<task-root>/<agent-name>/kb`
- task shared merge-oriented knowledge: task-local private worktree copy of `shared-kb`

Why:

- repo-root shared visibility is still useful;
- the collision problem is solved by task-local write surfaces, not by hiding the repository.

Alternative considered: launch from `<task-root>` instead of `<repo-root>`. Rejected for now because the wider shared visibility model is still valuable.

### Decision: Custom workspace contracts are explicit plan-owned path declarations

When pairwise-v3 uses `workspace_contract.mode = custom`, the plan should declare concrete paths and rules directly, for example:

- launch cwd
- source write paths
- shared writable paths
- bookkeeping paths
- read-only paths
- ad hoc worktree posture

Pairwise-v3 does not silently translate those paths into `houmao-ws/...`.

Why:

- custom mode exists exactly for operators who do not want the standardized Houmao layout;
- implicit translation would make custom mode dishonest.

Alternative considered: let pairwise-v3 loosely describe custom workspaces without explicit paths. Rejected because it would restore the same ambiguity this change is meant to remove.

### Decision: Runtime-owned recovery state stays separate in v3

Pairwise-v3 inherits the pairwise-v2 rule that runtime-owned recovery records remain Houmao-managed state, not part of the authored workspace or bookkeeping contract.

Examples:

- `<runtime-root>/loop-runs/pairwise-v2/<run_id>/record.json`
- `<runtime-root>/loop-runs/pairwise-v2/<run_id>/events.jsonl`

The v3 contract may reference operator-visible recovery notes, but it must not treat these runtime files as normal user-authored bookkeeping paths.

Why:

- recovery records are part of Houmao's runtime continuity model;
- operators and agents should not treat them as ordinary workspace notes.

Alternative considered: absorb recovery state into the workspace contract. Rejected because it blurs ownership and runtime semantics.

## Risks / Trade-offs

- [Risk] Having both v2 and v3 may confuse users. -> Mitigation: update loop authoring docs so v2 is the recovery/control-rich baseline and v3 is the workspace-aware extension.
- [Risk] Standard/custom at the loop-skill level may make users expect the workspace manager to understand both. -> Mitigation: state explicitly that `houmao-utils-workspace-mgr` remains standard-only.
- [Risk] Task-scoped in-repo posture is a breaking conceptual change from the current flat layout. -> Mitigation: document it clearly and keep the change localized to the standard in-repo model.
- [Risk] Custom workspace mode can become too underspecified. -> Mitigation: require concrete path declarations in the authored v3 contract.
- [Risk] Users may confuse runtime recovery files with custom bookkeeping. -> Mitigation: keep the docs and v3 spec explicit about the recovery boundary.

## Migration Plan

1. Add the new `houmao-agent-loop-pairwise-v3-skill` capability.
2. Update the workspace-manager spec so standard in-repo posture is task-scoped and remains standard-only.
3. Update packaged system-skill installation expectations to include pairwise-v3.
4. Update loop authoring docs to distinguish pairwise-v2 from pairwise-v3 and explain standard/custom workspace modes.
5. Implement the new packaged skill and aligned docs/assets.

Rollback is doc/spec/asset rollback only. No runtime data migration is required for this change.

## Open Questions

None for the proposal. The ownership boundary is now explicit:

- pairwise-v3 owns workspace contract choice,
- workspace-manager owns only the standard workspace,
- runtime recovery remains Houmao-owned state.
