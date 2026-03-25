## Context

The gateway runtime already owns a reusable live TUI tracking subsystem. `GatewayServiceRuntime.start()` calls `_start_tui_tracking_locked()`, which creates `SingleSessionTrackingRuntime` when `_tui_tracking_identity_locked()` can synthesize a `HoumaoTrackedSessionIdentity`.

Today, that identity builder admits only REST-backed attach contracts (`cao_rest` and `houmao_server_rest`). Attached runtime-owned `local_interactive` sessions already have working gateway execution through the local tmux-backed adapter, and their attach contracts already persist enough runtime-owned metadata to identify the session: backend kind, tmux session name, manifest path, runtime session id, and attach identity.

The shared tracking stack does not require a CAO terminal id. `HoumaoTrackedSessionIdentity` allows empty `terminal_aliases`, and the tracking layer falls back to `tracked_session_id` as the public `terminal_id` compatibility alias when no terminal alias is present. This change is therefore a gateway-local admission and identity-shaping change rather than a new tracking architecture.

## Goals / Non-Goals

**Goals:**
- Enable attached gateways for runtime-owned `local_interactive` sessions to start `SingleSessionTrackingRuntime`.
- Make the existing gateway-local TUI routes succeed for attached `local_interactive` sessions: current state, recent history, and explicit prompt-note tracking.
- Reuse existing attach metadata, manifest enrichment, and tracking runtime behavior rather than introducing a parallel tracking path.
- Keep the change hermetic to the gateway/runtime-owned session path and cover it with automated tests that do not require `houmao-server`.

**Non-Goals:**
- Redesign the shared tracking core, parser stack, or route models.
- Introduce a new attach-contract schema or a new backend-metadata shape for `local_interactive`.
- Change `houmao-server` managed-agent admission, discovery, or gateway projection behavior.
- Generalize gateway-owned TUI tracking to every tmux-backed headless backend in this change.

## Decisions

### 1. Admit `local_interactive` explicitly in gateway tracking identity synthesis

`_tui_tracking_identity_locked()` will be extended to synthesize a tracked identity for `backend == "local_interactive"` rather than returning `None`.

This keeps the scope narrow and matches the problem report exactly: prompt and interrupt execution already work for `local_interactive`, but gateway-owned tracking never starts because identity construction is gated too tightly.

Alternatives considered:
- **Add a new `local_interactive` attach metadata schema**: rejected because the existing runtime-owned attach contract already persists the fields needed for identity construction.
- **Admit all headless/tmux-backed backends at once**: rejected because the issue is specific to `local_interactive`, and widening the allowlist would mix this targeted fix with broader behavior changes that need separate review.

### 2. Use runtime-owned session identity as the canonical tracked session id

For attached runtime-owned `local_interactive` sessions, the tracked identity will use:

- `tracked_session_id = runtime_session_id or attach_identity`
- `session_name = tracked_session_id`
- `tmux_session_name = attach_contract.tmux_session_name`
- `tmux_window_name = None`
- `terminal_aliases = []`

This matches the runtime-owned gateway layout, where both `attach_identity` and `runtime_session_id` are already seeded from the runtime session id, and it avoids inventing a synthetic CAO-style terminal id for a path that does not have one.

Leaving `terminal_aliases` empty is intentional. The tracking layer already falls back to `tracked_session_id` as the public `terminal_id`, which yields a stable identity without adding compatibility metadata that the runtime does not naturally own.

Alternatives considered:
- **Use `backend_metadata.session_id` as the tracked id**: rejected because `local_interactive` does not depend on a persisted headless provider session id, while the runtime session id is always the canonical runtime-owned handle.
- **Use `tmux_session_name` as the tracked id**: rejected because the runtime session id is the stable storage and attach identity, whereas tmux names are a transport-facing surface.
- **Create a synthetic terminal alias**: rejected because empty aliases are already supported and the fallback behavior is explicit.

### 3. Reuse manifest enrichment but do not require manifest success for minimal identity

The gateway will continue attempting to enrich tracked identity from the session manifest to populate `tool`, `observed_tool_version`, `agent_name`, and `agent_id`.

If manifest loading fails, the gateway should still be able to construct the minimal identity needed to start tracking by falling back to durable attach-contract fields where possible, especially the tool name from headless-style backend metadata. This preserves current gateway robustness for runtime-owned sessions whose manifest enrichment is unavailable while keeping optional metadata best-effort.

Alternatives considered:
- **Require manifest parsing to succeed before tracking can start**: rejected because this would make gateway-owned tracking less resilient than the surrounding gateway control path.
- **Skip manifest enrichment entirely**: rejected because the manifest already provides the best available optional agent and tool provenance.

### 4. Keep tracking runtime startup and prompt-evidence flow unchanged once identity exists

No new tracking runtime class will be introduced. Once `_tui_tracking_identity_locked()` returns a non-`None` identity for `local_interactive`, existing gateway behavior should remain intact:

- `_start_tui_tracking_locked()` starts `SingleSessionTrackingRuntime`
- `GET /v1/control/tui/state` returns `tracking.current_state()`
- `GET /v1/control/tui/history` returns `tracking.history(limit=...)`
- successful `submit_prompt` execution records `note_prompt_submission(...)`

This minimizes implementation surface and ensures `local_interactive` participates in the same gateway-owned control-plane semantics as other attached tracked TUI paths.

Alternatives considered:
- **Create local-interactive-specific TUI routes**: rejected because the existing routes already model the desired contract.
- **Poll tmux directly inside the route handlers**: rejected because it would bypass the existing continuous tracking runtime and break consistency with the current gateway-owned tracking design.

### 5. Validate through gateway-focused automated coverage

Automated coverage should live with existing gateway support tests and exercise runtime-owned local attachability without involving `houmao-server`. The tests should verify:

- tracker startup for attached `local_interactive`
- successful gateway-local TUI state and history access
- prompt-submission evidence recorded on the gateway-owned tracker

This keeps the tests aligned with the actual scope of the change and avoids pulling in unrelated managed-agent infrastructure.

## Risks / Trade-offs

- **[Risk] Manifest enrichment may be missing or invalid for some runtime-owned sessions** → **Mitigation:** construct the minimal tracked identity from attach-contract data first, then treat manifest-derived fields as optional enrichment.
- **[Risk] Future local-interactive session layouts may expose a tmux window name and make `None` look incomplete** → **Mitigation:** keep `tmux_window_name` optional and allow later publication without changing the identity strategy introduced here.
- **[Risk] Broadening the identity gate too far could accidentally enable TUI routes for unsupported tmux-backed backends** → **Mitigation:** explicitly admit only `local_interactive` in this change.
- **[Trade-off] Public `terminal_id` for local-interactive gateway routes will be the runtime session id rather than a CAO-style terminal alias** → **Mitigation:** this is already a supported fallback in the tracking layer and matches the runtime-owned gateway identity model.

## Migration Plan

No data migration is required. Existing runtime-owned `local_interactive` attach contracts already persist the fields needed for this change.

Implementation consists of updating gateway identity synthesis and adding automated coverage. After deployment, newly attached gateways for runtime-owned `local_interactive` sessions will begin exposing the existing gateway-local TUI tracking routes without requiring any session re-registration or external coordination.

Rollback is straightforward: reverting the identity-admission change returns `local_interactive` gateways to the current unsupported-route behavior without requiring schema rollback or state conversion.

## Open Questions

- No blocking design questions remain for the initial implementation.
- A future follow-up may decide whether other runtime-owned tmux-backed backends should share the same gateway-owned TUI tracking admission path, but that is intentionally out of scope for this change.
