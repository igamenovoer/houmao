## Context

Houmao currently mixes three local default models:

- project overlays for catalog-backed project state and compatibility-projected agent definitions,
- shared per-user roots for runtime and mailbox state,
- working-directory-local scratch for job dirs.

That split is encoded across several layers rather than one shared contract. Project-aware commands resolve `agents/` through the active overlay, while build and launch flows still default runtime state through shared-root helpers, and mailbox/admin/server commands often keep their own root-resolution rules. As a result, a single "project-local" workflow commonly needs multiple environment overrides to keep state together.

This change redefines the local contract: when Houmao is operating in project context, the active project overlay becomes the default local state anchor for everything except the shared registry. Registry remains shared because it is the cross-project discovery surface.

## Goals / Non-Goals

**Goals:**

- Make local Houmao command flows resolve one active project overlay by default.
- Keep local Houmao-owned state under the active overlay by default:
  - `agents/`
  - `runtime/`
  - `jobs/`
  - `mailbox/`
  - `easy/`
  - catalog and managed content
- Keep only registry shared by default under `~/.houmao/registry`, subject to the existing env override.
- Remove the need for explicit `project init` as a prerequisite for maintained local project-aware workflows.
- Preserve explicit CLI overrides and existing env-var overrides as stronger precedence than project-aware defaults.
- Preserve shared-registry discovery so global `agents ...` resolution continues to work through absolute manifest pointers.

**Non-Goals:**

- Move registry under the project overlay by default.
- Remove the `project` command family.
- Change provider/runtime semantics unrelated to root resolution and project bootstrap.
- Auto-migrate or rewrite existing runtime/session artifacts in place under older shared roots.

## Decisions

### Decision: Introduce one central project-aware local-root resolver

Create one shared resolution path that returns the effective overlay-rooted local state family for commands that participate in project-aware behavior.

The effective default map is:

```text
overlay_root
agent_def_dir = <overlay>/agents
runtime_root  = <overlay>/runtime
jobs_root     = <overlay>/jobs
mailbox_root  = <overlay>/mailbox
easy_root     = <overlay>/easy
registry_root = ~/.houmao/registry  # unless existing registry env override redirects it
```

Rationale:

- The current split exists because each subsystem resolves roots independently.
- A central resolver makes the contract explicit and keeps future command families from drifting.

Alternative considered:

- Teach generic shared-root helpers such as runtime-root resolution to inspect `HOUMAO_PROJECT_OVERLAY_DIR` directly.
- Rejected because it would silently change behavior for every caller, including flows that are not intentionally project-aware.

### Decision: Use precedence `CLI > env > nearest discovered overlay inside the current Git worktree > bootstrap <cwd>/.houmao`

The active overlay is chosen in this order:

1. explicit CLI overlay/root selection,
2. `HOUMAO_PROJECT_OVERLAY_DIR`,
3. nearest ancestor discovered overlay within the current Git worktree boundary,
4. bootstrap `<cwd>/.houmao` when no overlay exists and the command needs local project-owned state.

Rationale:

- It preserves stable nested-directory workflows.
- It still honors the requested "create it if not found" behavior.
- It avoids creating multiple sibling overlays just because the operator runs commands from a nested subdirectory.
- It avoids inheriting a parent repository's `.houmao` when the operator is working inside a nested Git repository or worktree.

Alternative considered:

- Use exact `<cwd>/.houmao` only, with no nearest-ancestor discovery.
- Rejected because it would fragment one repo into many overlays depending on the caller's current directory.

Additional boundary rule:

- Discovery should stop at the current Git worktree root when one can be determined.
- CLI and env overrides remain allowed to point outside that boundary intentionally.

### Decision: Auto-bootstrap is applied to commands that require local state, not pure reporting/help paths

Commands that need a local Houmao-owned root to mutate or materialize state will ensure the overlay exists. Pure informational surfaces may report the selected overlay root without forcing creation.

Rationale:

- This keeps maintained workflows frictionless.
- It avoids surprising filesystem mutation from read-only inspection commands where creation is not necessary.

Alternative considered:

- Force overlay bootstrap for every command invocation.
- Rejected because it adds side effects to commands whose contract can remain read-only.

### Decision: Local launch/build flows must use overlay-local runtime and jobs explicitly

Project-aware local build and launch flows will pass explicit overlay-derived roots down into brain build and runtime session startup instead of relying on shared defaults.

This includes at minimum:

- local `brains build`,
- local `agents launch`,
- `project easy instance launch`,
- local server start paths that materialize Houmao-owned runtime artifacts.

Rationale:

- The current code already resolves agent-definition roots project-aware; runtime and jobs are the remaining split.
- Explicit propagation avoids hidden fallback behavior and keeps manifests, homes, sessions, and jobs coherent.

Alternative considered:

- Move only runtime sessions under the overlay and leave homes/manifests or jobs elsewhere.
- Rejected because it preserves the split-root inconsistency under a new name.

### Decision: Generic mailbox commands become project-aware by default in project context

When no explicit mailbox root is provided and no mailbox env override is set, generic mailbox commands resolve to the overlay mailbox root in project context.

Rationale:

- The mailbox root is part of the local project-owned state model under this change.
- It reduces the gap between `mailbox ...` and `project mailbox ...`.

Alternative considered:

- Leave generic mailbox commands shared-rooted and keep project mailbox as the only overlay-local mailbox surface.
- Rejected because it preserves a surprising split after the contract says all local operations are project-aware.

### Decision: Shared registry remains global and authoritative for cross-project discovery

Registry stays at the current shared-root contract unless explicitly redirected by the existing env override. Runtime/session manifests published in that registry may point to overlay-local absolute paths.

Rationale:

- The registry is the one intentionally shared discovery surface.
- Keeping it global preserves cross-project `agents ...` discovery and avoids turning registry lookup into a project-local-only feature.

Alternative considered:

- Make registry overlay-local too.
- Rejected because it undermines global name/addressed discovery and recovery, which is the registry's purpose.

## Risks / Trade-offs

- [Breaking local path defaults] → Update affected specs and docs explicitly; do not present this as backward-compatible.
- [Mixed old and new runtime locations] → Preserve absolute manifest-path handling so existing sessions under older roots continue to work until cleaned up.
- [Read-only command side effects become confusing] → Limit auto-bootstrap to commands that genuinely require local state materialization.
- [Global registry still allows cross-project name ambiguity] → Preserve current ambiguity behavior and keep agent-id or explicit selectors as the authoritative escape hatch.
- [Project-aware logic spreads inconsistently across command families] → Centralize overlay/root resolution behind one shared helper rather than duplicating fallback rules in each command.
- [Ancestor discovery can cross repo boundaries unexpectedly] → Bound implicit ancestor discovery to the current Git worktree while preserving explicit CLI/env escape hatches.
- [Server/admin commands may blur host-scoped and project-scoped maintenance] → Define project-context defaults carefully while preserving explicit CLI overrides for host-scoped administration.

## Migration Plan

1. Introduce the central project-aware root resolver and expose overlay-local `runtime` and `jobs` paths as first-class concepts.
2. Update project-aware build/launch command paths to pass explicit overlay-derived runtime and jobs roots.
3. Update mailbox, cleanup, and server command families to default to overlay-local roots in project context while preserving explicit overrides.
4. Update docs and workflow references that currently describe shared runtime or working-directory jobs as the default local project behavior.
5. Leave existing runtime artifacts in place; new sessions use the new defaults, while old sessions remain addressable through registry-published absolute manifest paths.

Rollback strategy:

- Because this is a contract change, rollback means restoring the previous default-root rules in the resolver and command boundaries, not migrating on-disk state back automatically.
- Existing artifacts created under overlay-local runtime/jobs remain readable because registry and manifest paths are absolute.

## Open Questions

- Should `project status` remain non-creating, or should it also bootstrap the overlay to make the "selected root" always concrete?
- Which generic command families are explicitly in scope for the first cut of "all Houmao operations project-aware": only maintained local CLI families, or also deprecated compatibility entrypoints on the same timeline?
