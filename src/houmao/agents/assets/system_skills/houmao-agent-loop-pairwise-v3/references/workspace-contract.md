# Workspace Contract

Use this reference when a pairwise-v3 plan needs to record where participants are supposed to work, where they may write, and how standard versus custom workspace mode changes that contract.

## Modes

Every pairwise-v3 plan records one workspace contract:

- `standard`
- `custom`

`standard` means the run uses Houmao's standard workspace posture.

`custom` means the run uses operator-owned paths and rules declared directly in the loop plan.

## Standard Mode

When the workspace contract uses `standard`, record:

- selected posture: `in-repo` or `out-of-repo`
- launch cwd or shared visibility surface
- private source-mutation surfaces
- shared writable surfaces when applicable
- default read-only surfaces
- ad hoc worktree posture
- authoritative workspace contract path, when one exists

### Standard In-Repo

Standard in-repo posture is task-scoped.

Task root:

```text
<repo-root>/houmao-ws/<task-name>
```

Key paths:

```text
<repo-root>/houmao-ws/workspaces.md
<repo-root>/houmao-ws/<task-name>/workspace.md
<repo-root>/houmao-ws/<task-name>/shared-kb/
<repo-root>/houmao-ws/<task-name>/<agent-name>/kb/
<repo-root>/houmao-ws/<task-name>/<agent-name>/repo/
```

Record:

- selected `task-name`
- repo root as the shared visibility surface when the standard contract uses `<repo-root>` as launch cwd
- task-local `workspace.md`
- task-local `shared-kb/`
- task-qualified branches such as `houmao/<task-name>/<agent-name>/main`

When the operator wants Houmao to prepare or summarize this standard layout, route that work to the standard workspace-preparation skill.

### Standard Out-Of-Repo

Standard out-of-repo posture continues to use the workspace-manager's standard out-of-repo layout. Record the selected workspace root, launch cwd, source repo bindings, private write targets, shared writable surfaces, and branch names exactly as prepared or summarized by the standard workspace contract.

## Custom Mode

When the workspace contract uses `custom`, record explicit operator-owned paths and rules directly in the plan.

At minimum, record:

- launch cwd
- source write paths
- shared writable paths, when applicable
- bookkeeping paths
- read-only paths
- ad hoc worktree posture

Custom mode does not translate those paths into Houmao-standard layout names.

## Bookkeeping Paths

Bookkeeping paths are part of the authored workspace contract, but their internal shape is task-specific.

Record:

- which paths are valid bookkeeping surfaces
- who may write them
- what they are for, when relevant

Do not impose one fixed subtree under per-agent `kb/`.

## Runtime-Owned Recovery Boundary

The workspace contract does not absorb Houmao runtime-owned recovery files.

These remain outside the authored workspace contract:

- `<runtime-root>/loop-runs/pairwise-v2/<run_id>/record.json`
- `<runtime-root>/loop-runs/pairwise-v2/<run_id>/events.jsonl`

Participants may inspect declared workspace and bookkeeping paths during recovery, but they should not treat runtime-owned recovery files as ordinary workspace notes.

## Guardrails

- Do not treat `custom` as shorthand for an unspecified workspace.
- Do not use the standard workspace-preparation skill as a custom-workspace translation layer.
- Do not prescribe a fixed bookkeeping subtree under per-agent `kb/`.
- Do not describe runtime-owned recovery files as authored workspace artifacts.
