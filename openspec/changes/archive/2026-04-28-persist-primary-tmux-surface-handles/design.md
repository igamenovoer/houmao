## Context

Houmao-owned tmux-backed managed-agent sessions currently model the primary agent surface as a stable textual target: `session:0.0`. That matches the intended public contract for Houmao-created and Houmao-joined sessions, where the primary managed-agent window is window `0` and the canonical primary pane is pane `0`.

tmux does not guarantee those indexes for newly created sessions. User configuration such as `base-index 1` and `pane-base-index 1` can create the first window as index `1` and its first pane as pane index `1`. In that environment, the current launch path fails while preparing the primary surface, and a partial launch may already have created runtime directories or mailbox registrations before the session becomes a live managed agent.

Gateway auxiliary windows already use tmux object handles (`@window_id`, `%pane_id`) for same-session gateway execution. The primary agent surface should use the same durable-handle pattern while keeping the operator-facing and manifest contract that the primary managed-agent window is window `0`.

## Goals / Non-Goals

**Goals:**

- Keep Houmao-owned primary managed-agent window index `0` as the contract for launch, join, relaunch authority, and diagnostics.
- Normalize newly created Houmao-owned tmux sessions so the primary managed-agent window exists at index `0`, regardless of the user's tmux `base-index`.
- Persist primary tmux object handles for the managed-agent surface, especially `tmux_window_id` and `tmux_pane_id`.
- Prefer `%pane_id`/`@window_id` for runtime control, capture, prompt submission, interruption, and health checks when valid.
- Refresh stale primary handles from the contractual primary surface when the window `0` authority remains intact.
- Fail explicitly when the primary surface is missing, ambiguous, or no longer satisfies the managed-agent window `0` contract.

**Non-Goals:**

- Do not allow Houmao-owned primary managed-agent windows to live at arbitrary indexes.
- Do not redesign gateway auxiliary-window identity beyond reusing its durable-handle pattern.
- Do not require migration tooling for older manifests; missing handles can be lazily resolved from the existing tmux session authority.
- Do not preserve legacy launch behavior that depends on user tmux default indexes.

## Decisions

1. Preserve index `0` as contract, use tmux IDs as live handles.

   Houmao should continue to publish and validate `primary_window_index = "0"` in session manifests and relaunch authority. The new data model supplements this with `primary_window_id` and `primary_pane_id` so operations do not repeatedly reconstruct `session:0.0`.

   Alternative considered: replace index-based authority entirely with `@window_id` and `%pane_id`. That would make operation targeting robust but would weaken the established join/launch contract and make operator-facing diagnostics less predictable.

2. Normalize the tmux-owned primary surface during launch.

   After creating a tmux session, Houmao should discover the bootstrap window/pane by live tmux identity, move that window to `session:0` when needed, normalize pane addressing for that window when needed, rename/select the primary window by `@window_id`, and return the resulting surface record.

   Alternative considered: query `base-index` and target the configured first window. That avoids the immediate rename failure but breaks the Houmao primary-window `0` contract and leaves later `session:0` health/relaunch checks inconsistent.

3. Persist primary handles in manifest-backed backend state.

   Headless and local-interactive backend state should store the primary `tmux_window_id` and `tmux_pane_id` alongside `tmux_session_name` and `tmux_window_name`. Manifest `tmux` and `agent_launch_authority` sections should include the same secret-free handles when known.

   Alternative considered: keep handles only in memory. That would fix the first launch operation but would not help later CLI invocations, server fallback interruption, relaunch, or local discovery.

4. Resolve on use with validation and lazy repair.

   When a runtime operation has a persisted `%pane_id`, it should first confirm that pane exists in the expected session and belongs to primary window index `0`. If the handle is stale, the runtime should attempt to resolve the primary surface from window index `0` plus the expected managed-agent window name or canonical pane constraints, then refresh the persisted handles. If resolution fails, the operation should report degraded or stale authority rather than guessing from current focus.

   Alternative considered: always re-resolve from `session:0.0`. That leaves the system exposed to pane-base-index differences and misses the value of persisted tmux object handles.

5. Keep joined-session adoption stricter than launch normalization.

   `houmao-mgr agents join` already requires the adopted surface to be window `0`, pane `0`. This change should keep that requirement, discover the live `@window_id` and `%pane_id` for that surface during adoption, and persist them for later operations. It should not silently move or reshape an operator-owned tmux session during join.

   Alternative considered: normalize joined sessions like created sessions. That would be surprising because join adopts an existing operator surface and should avoid rearranging user-owned tmux layouts without explicit consent.

## Risks / Trade-offs

- Existing manifests may not contain primary tmux object handles. → Treat missing handles as recoverable and lazily resolve them from existing `tmux.session_name`, `primary_window_index`, and `primary_window_name`.
- Persisted handles can become stale if a user kills or moves panes manually. → Validate handles before use and refresh only when the primary window `0` contract still identifies a single valid surface.
- tmux pane indexes are harder to normalize than window indexes. → Prefer `%pane_id` after launch; normalize pane indexing for Houmao-created sessions where practical, but do not make later operations depend solely on `.0`.
- Moving a bootstrap window to index `0` may conflict with an unexpected existing window. → Fresh Houmao-created sessions should contain only the bootstrap window; if multiple windows exist during normalization, fail closed rather than using `move-window -k` to destroy user-visible state.
- Updating schema and manifests touches several layers. → Implement with optional fields first, then update writers/readers/tests together so older manifests remain readable.

## Migration Plan

1. Extend boundary models and JSON schemas with optional primary `tmux_window_id` and `tmux_pane_id` fields.
2. Add tmux runtime helpers that prepare, resolve, validate, and refresh the primary surface as a structured record.
3. Store handles on new launches, relaunches, and joins.
4. Update runtime operations to target `%pane_id` when valid and fall back to contract-based refresh when missing or stale.
5. Keep older manifests readable by allowing missing handles and resolving them lazily during the first operation that needs the primary surface.
6. Rollback is limited to reverting the code/schema change; manifests containing extra optional fields should remain parseable by the updated strict schemas but may not be understood by older package versions.

## Open Questions

- Should Houmao-created sessions forcibly set window-local `pane-base-index 0`, or is persisting `%pane_id` sufficient once the initial pane is discovered?
- Should primary `tmux_window_id` and `tmux_pane_id` live only under the normalized `tmux` manifest section, or should backend-specific sections duplicate them for easier resume-state construction?
- Should the shared registry expose primary tmux handles publicly, or keep them manifest-local and resolve through manifest reads?
