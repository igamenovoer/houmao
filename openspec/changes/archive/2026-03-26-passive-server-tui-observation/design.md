## Context

The passive server currently discovers agents from the shared registry and proxies gateway requests (steps 2–3 of the greenfield migration). Step 4 adds TUI observation: the ability to watch each discovered agent's tmux pane and serve parsed observation state through HTTP.

The codebase already has well-tested TUI tracking infrastructure split across two locations:

1. **`shared_tui_tracking`** — core tracking session (`TuiTrackerSession`), detector profiles (Claude, Codex, fallback), signal detection, state models (`TrackedStateSnapshot`, `DetectedTurnSignals`, etc.), and stability tracking. This is tool-agnostic and reusable.

2. **`server/tui/`** — server-side integration: `TmuxTransportResolver` (pane capture), `PaneProcessInspector` (process liveness), `OfficialTuiParserAdapter` (parser wrapper), `LiveSessionTracker` (per-session state management), and `TuiTrackingSupervisor` (worker pool management). Response models like `HoumaoTerminalStateResponse` and `HoumaoTerminalHistoryResponse` live in `server/models.py`.

The existing server's TUI tracking couples tightly to its registration-backed session management (`KnownSessionRegistry`, `terminal_id` addressing, CAO-era lifecycle). The passive server replaces this lifecycle with discovery-index-driven observer management.

## Goals / Non-Goals

**Goals:**
- Provide per-agent TUI observation state via three HTTP endpoints (compact state, detailed state, transition history).
- Reuse existing shared infrastructure (`TuiTrackerSession`, detectors, transport, process inspector, parser) without forking.
- Integrate observation lifecycle with the existing `RegistryDiscoveryService` so observers are created/removed automatically as agents appear/disappear.
- Support all currently supported tools (Claude Code, Codex) with version-aware detector selection.

**Non-Goals:**
- No turn anchoring or prompt submission tracking in this step. Turn anchor lifecycle is deferred to step 5/6 (headless agent management and request submission). The observation layer tracks state passively — it does not accept `note_prompt_submission()` calls.
- No direct reuse of `LiveSessionTracker` or `TuiTrackingSupervisor`. These classes are tightly coupled to the old server's registration model and response serialization. The passive server builds a simpler observer that composes the same underlying components.
- No `terminal_id` addressing. The passive server addresses agents by `agent_ref` (id or name).
- No operator state or lifecycle authority tracking. These are server-owned concepts that depend on turn anchoring and headless authority, which are out of scope for this step.

## Decisions

### Decision 1: Shared polling loop, not per-agent threads

The observation service uses a single background thread that iterates over all active observers each cycle (configurable interval, default 2s). This is simpler than per-agent threads and sufficient for the expected agent count (<50 agents).

**Why not per-agent threads?** More complex lifecycle management, harder to reason about shutdown ordering, no benefit until agent count exceeds ~100.

### Decision 2: Observer reconciliation driven by discovery index snapshots

Each polling cycle, the observation service reads the current discovery index (`list_all()`), compares agent IDs against active observers, and creates/removes observers as needed. This is a full-rebuild reconciliation model, consistent with how the discovery service itself works.

**Why not event-driven?** The discovery index is rebuilt atomically each scan cycle. There is no event stream to subscribe to. Snapshot comparison is simple and correct.

### Decision 3: New `AgentTuiObserver` class, not reuse of `LiveSessionTracker`

`LiveSessionTracker` from `server/tui/tracking.py` is ~600 lines that include turn anchoring, operator state pipelines, lifecycle authority tracking, and `HoumaoTerminalStateResponse` serialization — most of which is out of scope for this step. Instead, build a simpler `AgentTuiObserver` that directly composes:

- `TuiTrackerSession` (from `shared_tui_tracking`) for core state tracking
- `TmuxTransportResolver` (from `server/tui/transport.py`) for pane capture
- `PaneProcessInspector` (from `server/tui/process.py`) for process liveness
- `OfficialTuiParserAdapter` (from `server/tui/parser.py`) for TUI parsing

The observer manages per-agent mutable state: resolved tmux target, parser baseline position, last probe snapshot, and the tracking session itself.

**Why not wrap `LiveSessionTracker`?** It would require stubbing or disabling turn anchoring, operator state, and lifecycle authority features. The result would be more code than building a focused observer from the shared components.

### Decision 4: Response models wrap existing sub-models

Create new top-level response models (`AgentTuiStateResponse`, `AgentTuiDetailResponse`, `AgentTuiHistoryResponse`) in `passive_server/models.py` that:

- Use `agent_id` and `agent_name` as identification (not `terminal_id`)
- Embed existing sub-models from `server/models.py`: `HoumaoTrackedDiagnostics`, `HoumaoParsedSurface`, `HoumaoProbeSnapshot`, `HoumaoTrackedSurface`, `HoumaoTrackedTurn`, `HoumaoTrackedLastTurn`, `HoumaoStabilityMetadata`, `HoumaoRecentTransition`
- Compact state omits `probe_snapshot` and `parsed_surface` (served only in detail endpoint)

This gives the passive server its own API identity while reusing all the well-tested diagnostic sub-models.

### Decision 5: Tool version detection from TUI output, not registry

The registry record does not include the agent's tool version. The observer resolves the detector profile by:

1. Reading `tool` from the registry record's `identity.tool` field.
2. On the first successful pane capture, attempting version detection from the output text (each tool-specific detector can extract version strings from TUI output).
3. Falling back to the tool's fallback detector if version detection fails.

This mirrors how the existing server resolves detectors.

### Decision 6: Observation poll interval separate from discovery poll interval

The observation poll interval (default 2s) is independent of the discovery poll interval (default 5s). Observation needs faster refresh to detect state transitions promptly. Add `observation_poll_interval_seconds` to `PassiveServerConfig`.

## Risks / Trade-offs

- **[Import coupling to `server/tui/`]** → The passive server imports `TmuxTransportResolver`, `PaneProcessInspector`, and `OfficialTuiParserAdapter` from the old server's TUI module. If the old server is deleted in step 8, these classes must be relocated (e.g., to `shared_tui_tracking` or a new `houmao.tui` package). This is acceptable for now — the greenfield plan explicitly defers code reorganization to step 8.

- **[Import coupling to `server/models.py`]** → Sub-models like `HoumaoTrackedDiagnostics` and `HoumaoParsedSurface` are imported from the old server. Same relocation concern as above.

- **[No turn anchoring]** → Without turn anchoring, the observation layer cannot distinguish "ready because the turn completed" from "ready because the agent was already idle". This is acceptable for step 4 — turn anchoring requires request submission integration (step 5/6).

- **[Shared polling loop latency]** → With 50 agents at 200ms per poll cycle, one full iteration takes ~10s. If observation latency becomes an issue, the loop can be split into parallel batches. Not needed initially.

## Open Questions

None — design decisions are sufficient for implementation.
