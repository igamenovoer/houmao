## Context

Project-aware overlay resolution is already centralized in `src/houmao/project/overlay.py`. Today the ambient selection contract is:

1. explicit CLI overlay or agent-definition override when available,
2. `HOUMAO_PROJECT_OVERLAY_DIR`,
3. nearest ancestor `.houmao/houmao-config.toml` bounded by the current Git worktree,
4. fallback or bootstrap `<cwd>/.houmao`.

That default is useful for repo-wide behavior, but it makes parent overlay inheritance mandatory whenever a caller works under a repository subtree. The requested change is to keep the current default while adding one opt-in environment control that disables ancestor search and treats only `<cwd>/.houmao` as the ambient overlay candidate.

This is a cross-cutting change because all maintained project-aware command families already depend on the shared overlay resolver, and operator-facing result wording plus docs describe the current precedence contract.

## Goals / Non-Goals

**Goals:**

- Add one environment variable that switches ambient overlay discovery between the current nearest-ancestor behavior and a cwd-only mode.
- Preserve the current default behavior when the new env is unset.
- Apply the new mode consistently across project-aware command surfaces by changing the shared resolution layer once.
- Surface the effective discovery mode clearly in project-aware status or diagnostic output where the overlay-selection contract is reported.

**Non-Goals:**

- Change `houmao-mgr project init` target semantics away from `<cwd>/.houmao` when no explicit overlay-dir override is set.
- Replace `HOUMAO_PROJECT_OVERLAY_DIR` or weaken its precedence.
- Add a new config-file setting in `houmao-config.toml` for discovery mode.
- Introduce per-command CLI flags for discovery mode in this change.

## Decisions

### Decision: Add `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` as the single ambient-discovery switch

The system will add one env var, `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`, with these values:

- `ancestor`: current behavior; search nearest ancestor `.houmao/houmao-config.toml` within the current Git worktree boundary.
- `cwd_only`: skip parent search and only inspect `<cwd>/.houmao/houmao-config.toml` as the ambient discovery anchor.

When the env is unset, the effective mode is `ancestor`.

Rationale:

- Discovery happens before a project config is loaded, so the switch must live outside `houmao-config.toml`.
- An env var matches the existing project-aware override model (`HOUMAO_PROJECT_OVERLAY_DIR`, `HOUMAO_AGENT_DEF_DIR`, root overrides).
- One global mode is enough for the operator need described here and avoids new CLI surface area.

Alternatives considered:

- Store the mode in `houmao-config.toml`: rejected because the system must discover the overlay before it can read that file.
- Add a CLI flag to every project-aware command: rejected because the behavior is centrally shared and the per-command surface would be noisy and repetitive.

### Decision: Implement the mode only in the shared overlay resolver

The mode will be applied inside `resolve_project_overlay()` and any helper it delegates to for ambient discovery. All higher-level helpers such as `resolve_project_aware_agent_def_dir()`, `resolve_project_aware_local_roots()`, `ensure_project_aware_local_roots()`, and the runtime/build command paths will inherit the behavior automatically.

Rationale:

- The current implementation already funnels project-aware resolution through this layer.
- This keeps the behavioral contract consistent for `agents launch`, `agents join`, `brains build`, `project status`, mailbox flows, cleanup, and server commands.

Alternatives considered:

- Branch per command family: rejected because it duplicates policy and creates drift between launch, status, and non-launch surfaces.

### Decision: Keep `HOUMAO_PROJECT_OVERLAY_DIR` precedence above discovery mode

If `HOUMAO_PROJECT_OVERLAY_DIR` is set, it continues to select the overlay root directly. Discovery mode only affects ambient lookup when no explicit overlay-root override is present.

Rationale:

- `HOUMAO_PROJECT_OVERLAY_DIR` is already the strongest project-overlay selector.
- Operators using an explicit overlay root should not need to reason about ancestor-vs-cwd ambient behavior for that invocation.

Alternatives considered:

- Make `cwd_only` suppress `HOUMAO_PROJECT_OVERLAY_DIR`: rejected because it would make the stronger override surprisingly weaker than an ambient mode toggle.

### Decision: Report discovery mode separately from overlay-root source

The resolution payload should track the effective discovery mode separately from `overlay_root_source`.

Rationale:

- `overlay_root_source` answers “where did the selected root come from?” (`env`, `discovered`, `default`).
- Discovery mode answers “how was ambient discovery constrained?” Those are orthogonal facts.
- Reusing `overlay_root_source` alone would make `project status` wording ambiguous in cwd-only mode.

Alternatives considered:

- Overload `overlay_root_source` with more enum values such as `cwd_discovered`: rejected because it mixes source and policy into one field and complicates existing wording.

### Decision: Invalid discovery-mode values fail explicitly

Unsupported values for `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` will raise a clear error instead of silently falling back to the default mode.

Rationale:

- Silent fallback would make operators think cwd-only isolation is active when it is not.
- The existing project-overlay env contract already prefers explicit validation for bad inputs such as relative overlay-dir overrides.

Alternatives considered:

- Silently default invalid values to `ancestor`: rejected because it hides misconfiguration.

## Risks / Trade-offs

- [Operators may export `cwd_only` broadly and stop inheriting a repo-level overlay unexpectedly] -> Mitigation: keep `ancestor` as the default, document the scope clearly, and surface the active discovery mode in status/detail payloads.
- [Status and result wording may become inconsistent if some command surfaces do not expose the new mode] -> Mitigation: plumb the mode through shared resolution dataclasses and shared operator-wording helpers rather than ad hoc strings.
- [Tests may overfit current `overlay_root_source` wording] -> Mitigation: update unit and CLI shape tests alongside the shared wording contract instead of patching individual failures piecemeal.

## Migration Plan

No filesystem or catalog migration is required.

- Existing operators get unchanged behavior because the new env defaults to `ancestor`.
- Operators who want strictly local overlay scoping set `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=cwd_only`.
- Rollback is trivial: unset the env or set it back to `ancestor`.

## Open Questions

- None for the functional contract. The only remaining implementation choices are naming consistency in payload fields and exact wording strings for status/help surfaces.
