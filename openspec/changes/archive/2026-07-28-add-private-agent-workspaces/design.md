## Context

Most agents should continue running in the selected user project. Some definitions also need private, instance-owned storage with named semantic directories. The workspace must remain understandable to Houmao without a definition-specific harness.

The managed-agent instance-state change provides canonical agent identity and mindset records. This change adds an optional auxiliary workspace. It does not replace the project workdir or the canonical instance-state database.

## Goals / Non-Goals

**Goals:**

- Let definitions declare stable semantic workspace labels.
- Materialize one safe project-contained workspace per instance.
- Keep stable topology in TOML and growing metadata in SQLite.
- Let humans adjust paths without changing skill instructions.
- Default to local-untracked Git posture.
- Support verified-self path reads and explicit admin mutation.

**Non-Goals:**

- Mandatory private workspaces.
- Automatic workdir replacement when private storage is enabled.
- External workspace roots.
- OS-level isolation.
- Standard multi-agent worktrees.
- Canonical runtime variables or mindset records in the workspace.

## Decisions

### Separate Execution Workdir From Private State

The instance contract declares:

- optional Private Agent Workspace Contract;
- activation mode: `disabled`, `optional`, or `required`;
- default deployment selection;
- workdir mode: `project-root` or `private-root`.

`private_state_root` and `execution_workdir` are separate resolved fields. Enabling a private workspace leaves the process in the user project unless `workdir_mode = "private-root"` is explicitly declared and selected.

### Keep the Manifest Stable

`houmao-agent-workspace.toml` stores:

- manifest schema version;
- workspace id and managed-agent id;
- project, deployment, definition, and workspace-contract identities;
- workspace-contract digest;
- semantic label to confined relative path bindings;
- tracking posture;
- SQLite filename and schema version.

It does not store a database digest, mutable generation, record arrays, or payload inventory.

`houmao-agent-workspace.sqlite` stores:

- its own schema and current generation;
- repeated workspace identity for cross-file validation;
- growing record metadata;
- payload paths and digests;
- projection metadata and revisions.

The manifest remains unchanged when only indexed records change.

### Use Semantic Labels as the Stable Interface

The definition declares labels such as `workspace.artifacts` or `workspace.mindsets`, expected path kinds, default relative paths, required posture, and materialization policy.

Admin mutation changes only a concrete binding. It cannot add, remove, or redefine labels for one instance. Paths must remain relative, confined, non-symlinked at mutation boundaries, unique where required, and type-compatible.

Static skills refer to labels and use verified-self lookup. They do not hard-code default directories.

### Prepare Workspaces Through the Launch State Machine

Launch allocates a unique root inside the selected project and records workspace preparation in canonical instance state. Preparation:

1. validates the exact workspace contract and deployment selection;
2. checks path ownership and collisions;
3. creates operation-owned staging;
4. writes TOML and initializes SQLite;
5. materializes required semantic paths;
6. establishes the requested Git posture;
7. publishes the root;
8. records the association before process start.

Each step is idempotent. Failure records evidence and removes only fresh operation-owned staging when safe. Existing compatible preserved workspaces are revalidated and reused.

### Use Repository-Local Ignore State by Default

`local-untracked` verifies that the proposed root is not in the repository index and is effectively ignored. Houmao maintains an owned entry in `.git/info/exclude`.

An inner `.gitignore` does not prove that the parent repository ignores the root. Houmao never stages files, commits, pushes, runs `git rm --cached`, or mutates a tracked project `.gitignore` as part of this feature.

Explicit human opt-in changes the manifest posture to `tracked-permitted` and removes only Houmao's owned exclude entry.

### Keep Mindset Projections Non-Canonical

A workspace contract may bind a projection label such as `workspace.mindsets`. An explicit operation publishes one immutable mindset revision payload and indexes it in workspace SQLite.

Editing or deleting the projection never changes canonical `state.sqlite`. Validation reports drift. Explicit refresh republishes the selected canonical revision.

### Preserve User Artifacts on Removal

Stopping or preserving an instance retains its workspace association. Ordinary managed-agent removal preserves private workspace contents by default.

Destructive cleanup requires an explicit target, ownership and digest checks, repository-state checks, and confirmation. Drift blocks cleanup until the human resolves or explicitly adopts the affected content through a separate safe operation.

## Risks / Trade-offs

- [Users confuse private storage with a sandbox] -> Document that confinement is path validation, not OS isolation.
- [TOML and SQLite point to different workspaces] -> Repeat workspace identity in both and validate it without hashing the mutable database.
- [A root becomes tracked after creation] -> Recheck index and effective-ignore posture in doctor and before mutation.
- [Process startup fails after workspace publication] -> Preserve launch-attempt state and clean only fresh operation-owned content.
- [A user edits a projection] -> Report drift and keep canonical instance state unchanged.

## Migration Plan

1. Extend the Agent Definition instance-contract schema.
2. Add workspace TOML and SQLite schemas.
3. Add launch preparation and preserved-instance validation.
4. Add semantic path lookup and admin binding mutation.
5. Add Git posture management and doctor.
6. Add mindset projection and explicit cleanup.
7. Update system skills, behavior tests, and documentation.

## Open Questions

None block v1. External roots, workspace sharing, and OS-level isolation require separate changes.
