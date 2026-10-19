# Design

## Context

See proposal.md for motivation. Architecture facts that shape this design, verified against the current code:

- Three independent consumers track a session from tmux pane text: the `houmao-server` poll loop (`src/houmao/server/service.py:1776`), the gateway-owned `SingleSessionTrackingRuntime` (`src/houmao/shared_tui_tracking/ownership.py:133`), and the passive server's `AgentTuiObserver` (`src/houmao/passive_server/observation.py:95`). All poll at 0.5 s by default.
- `LiveSessionTracker` (`src/houmao/server/tui/tracking.py:106`) is a pure in-memory reducer driven by caller-pushed `record_cycle(...)` and `note_prompt_submission(...)`. It already reconciles two authorities at projection time: `TuiTrackerSession` facts (which own `last_turn`) and lifecycle-kernel facts (`_build_tracker_last_turn`, `_align_operator_state_with_tracker_state`, `tracking.py:1773` and `:1821`). Its `HistoricalScheduler` advances only when a poll cycle runs (`tracking.py:989`).
- `session_root` is already threaded through every tracking consumer (`HoumaoTrackedSessionIdentity.session_root`, `src/houmao/server/models.py:166`); the passive server reads it from registry records.
- `_publish_tmux_session_environment` (`src/houmao/agents/realm_controller/backends/headless_base.py:577`) publishes `os.environ` plus `plan.env` into the tmux session environment — anything in `plan.env` becomes visible to any process that can attach the tmux session.
- `ensure_claude_home_bootstrap` (`src/houmao/agents/realm_controller/backends/claude_bootstrap.py:17`) owns and validates the managed home's `settings.json`, so unmanaged merges into it are fragile.
- The Claude 2.1.296 support floor is already centralized in the launch policy (`src/houmao/agents/launch_policy/registry/claude.yaml:10`) and the detector registry (`src/houmao/shared_tui_tracking/registry.py:126`).
- The prior design exploration lives in `context/features/2026-10-18-cli-hook-observation-channel/`; this design resolves its open questions. Decisions follow the repository's simplification principles: reuse existing infrastructure, avoid new dependencies and speculative machinery, and keep the smallest complete v1.

## Goals / Non-Goals

**Goals:**

- Managed Claude `local_interactive` sessions gain hook-derived lifecycle facts merged into tracked state, with TUI-only behavior byte-equivalent whenever the channel is not active.
- One collector per session; raw events in one session-local store; all consumers read the same store.
- No new third-party dependencies; minimal wiring into existing launch, tracking, gateway, and passive-server paths.
- Qualification evidence that the merge is correct and that TUI-only behavior is preserved.

**Non-Goals:**

- Default-on rollout (this change is opt-in; default-on is a follow-up after qualification gates pass).
- `claude_headless`, joined sessions, unmanaged launches, Codex/Kimi adapters.
- Publishing hook-derived final assistant text, automatic remediation.
- Re-platforming `TuiTrackerSession` or the lifecycle kernel onto a single unified stream.

## Decisions

### D1. Standalone collector; the event store is the fan-out point

One standalone collector process per session, started before the provider, bound to `127.0.0.1` on an ephemeral port, authenticating with a per-session bearer token. It validates, stamps (`channel_generation`, `sequence`, `received_at_utc`), appends to `<session_root>/hook-observation/claude/events.ndjson` (mode `0600`), maintains a secret-free `channel.json`, and acknowledges before doing any heavy work. Every tracking consumer (gateway runtime, houmao-server, passive server) runs a small reader that tails `events.ndjson` with its own offset and feeds its local tracker.

Rationale: the collector cannot push into consumers' in-process Rx subjects — it is a separate process and up to three consumers track one session. A file tail reuses a proven primitive (append-only NDJSON) and matches the passive server's existing file-based discovery model. Alternatives rejected: gateway-hosted collector (the gateway may attach after the provider starts); a multi-client socket protocol (new machinery for a problem the file already solves); in-process collection (only one consumer would see events).

### D2. Hook posture merges as a third authority at the tracker's existing projection layer

Each consumer reduces its read events into a compact hook posture with a small pure reducer driven through `ops.scan` on the tracker's existing `HistoricalScheduler`. `LiveSessionTracker` then applies the authority table where it already reconciles two authorities: `_build_tracker_last_turn` (hook terminal settles `success`/`known_failure`; TUI keeps `interrupted`) and `_align_operator_state_with_tracker_state` (hook active/blocked/maintenance holds `turn.phase` against a false-ready surface). `TuiTrackerSession` is untouched and stays the TUI-only channel. The normative transition rules for the merged state (including the hook-only `blocked` phase and the session-scoped `work` axis) live in [design/state-transitions.md](design/state-transitions.md).

Rationale: the reconciliation seam already exists and is tested; adding a third authority there is the smallest change that satisfies the authority table. Alternatives rejected: one grand `merge` of hook+TUI+lifecycle raw streams (rewrites the proven `TuiTrackerSession` decision tree for no behavioral gain); feeding hook events into `TuiTrackerSession` (violates its hook-free contract and would change TUI-only semantics).

### D3. Hook events fold at poll-cycle boundaries

Readers deliver observations into the tracker at the next `record_cycle` (worst case the existing 0.5 s poll interval), stamped with ingest order. No out-of-cycle wake machinery in v1.

Rationale: the tracker's scheduler only advances during cycles, so queue-and-fold needs no new threading or timer model. Revisit trigger: measured completion-detection latency in live qualification; if the 0.5 s bound proves insufficient for admission responsiveness, add a wake-on-terminal event later.

### D4. The collector token rides the provider-process environment only

The token is generated per session and placed in the provider process environment through the backend's launch wrapper (the `bash -lc` script built by `local_interactive`), which command hooks inherit as children of the provider. It is never added to `plan.env`, because `_publish_tmux_session_environment` publishes plan env into the tmux session environment. Observer settings reference the token through the provider's allowed-env-var mechanism.

Rationale: fixes the leak at the owning boundary instead of filtering at publication time. Alternative rejected: `0600` token file (works, but a second credential path to secure and clean up; can be added later if a provider mode cannot inherit env).

### D5. Managed-home marker merge is the primary injection; `--settings` is the fallback

**Correction (2026-10-19, campaign iteration 1):** the original D5 chose `--settings`-only injection with conflict-to-unavailable. Live evidence flipped the primary path. The corrected decision:

The launch plan installs the observer configuration by marker-merging a Houmao-owned hook block into the managed home's `settings.json` (the `CLAUDE_CONFIG_DIR` user-settings layer) at every launch generation, preserving bundle-projected and operator-authored entries. The home is a runtime-owned surface (`src/houmao/agents/launch_policy/registry/claude.yaml:19`, owned paths and `json.set` actions), one home has at most one live session, and `claude_bootstrap` already owns and validates that file. The session-scoped `--settings <observer-settings.json>` argument is demoted to the fallback for launch profiles where the home file cannot be safely merged (for example a projected read-only home); it is no longer the primary path.

The merge is marker-based: the observer block is identified by its command/URL markers, never by a new provider field, and the installer rewrites the block at every launch and every resume/relaunch generation (new collector port and token each time). On a reused home, a stale observer block from an earlier generation is repaired in place; bundle and operator hook entries are preserved. A stale port inside a preserved home block (for example after an unclean stop, until the next launch rewrites it) is benign: deliveries to the dead collector fail closed at the hook handler, which always exits 0 and never blocks the provider.

Conflict semantics, corrected: managed `realm_controller` launch plans build their args from the resolved launch behavior plus policy/provider-generated args with no operator-controlled passthrough (verified against `src/houmao/agents/launch_policy/` and `realm_controller/launch_plan.py`, 2026-10-19), so a double `--settings` cannot occur on the managed path. The raw operator-facing launch-helper CLI (`launch_policy/cli.py`) does append a `--` passthrough and the claude policy currently owns only `--dangerously-skip-permissions`; hardening that helper to own or reject `--settings` is a named follow-up. Joined sessions and unmanaged launches remain `unavailable` (their homes and args are not Houmao-owned). If the fallback `--settings` path is ever used and the resolved args already contain a settings source, the channel reports `unavailable` with a settings-conflict detail and the session continues TUI-only.

Rationale (original): `--settings` is session-scoped and leaves operator and managed-home settings untouched; the managed-home merge fallback requires cooperating with bundle projection and validation in `claude_bootstrap` for no demonstrated consumer. Revisit trigger: the first real launch profile that must combine its own `--settings` with hook observation. **Why corrected:** the campaign evidence showed the managed-home merge works end to end (operator hooks coexist undisturbed, token env interpolation clean, payload parity with the `--settings` path, SessionStart under 1 s), that fresh scratch homes need the seeded project-trust keys the bootstrap already owns, and that the managed path never needs `--settings` at all. Evidence: campaign `context/campaigns/debug/2026-10-19-claude-hook-observation/evidences/2026-10-19-home-injection-coexistence.md` (coexistence arm), plus the iteration-1 set `2026-10-19-s0-gate-smoke.md`, `2026-10-19-s1-normal-multiturn.md`, and `2026-10-19-floor-2-1-296-s1-repeat.md` (floor verification at 2.1.296).

### D6. v1 event set: nine events

Required: `SessionStart` (command hook; HTTP hooks cannot deliver it), `UserPromptSubmit`, `Stop`, `StopFailure`, `PermissionRequest`, `PreCompact`, `PostCompact`, `PostToolUse`, `PostToolUseFailure` (all HTTP where supported). Excluded from v1: `PostToolBatch`, `SubagentStart/Stop`, `Notification`, `SessionEnd`, `PreToolUse`, and everything P3 — none of them unlock a v1 use case. `background_work_pending` comes from the `Stop` payload, which v1 already collects.

Rationale: smallest set covering all four feature use cases (enable/verify, normal-turn merge, permission+failure detection, fallback). `PostToolUse` is the highest-frequency event; qualification includes a latency measurement gate, and if it proves hot the adapter drops it (posture stays correct: `UserPromptSubmit`→`Stop` still brackets activity) rather than adding async-hook machinery.

### D7. Opt-in enablement through one environment flag

`HOUMAO_HOOK_OBSERVATION_CLAUDE=1` (or a launch-profile field mapping to it) enables the channel for new managed Claude launches. Absent or any other value means exactly today's behavior.

Rationale: one rollback control, no public CLI surface to support yet. Alternative rejected: per-launch CLI flag (public surface before qualification gates pass).

### D8. Public surface is additive and minimal

`HoumaoTerminalStateResponse` gains optional `observation_channels`; `HoumaoTrackedDiagnostics` gains optional hook counters/conflict reasons; gateway status and admission decision records carry hook facts; `TrackedLastTurnSource` gains `hook_observation`. Hook-derived final assistant text and `bound_session_id` stay local-only in v1; the passive server reads `channel.json`/`events.ndjson` when local and reports `unavailable` with `detail="remote observation"` otherwise.

Rationale: additive optional fields keep every existing consumer working; publishing final text is a policy decision deferred until there is a consumer for it.

### D9. One new neutral subpackage, stdlib-only collector and emitter

New code lives in `src/houmao/hook_observation/`: envelope/store, normalizer, posture reducer, collector (stdlib `http.server` on a thread), and the command-hook emitter script (stdlib only, always exits 0). Tracking/gateway/passive wiring stays in the existing modules that own those seams. `reactivex` is already a dependency; nothing else is added.

Rationale: mirrors the `src/houmao/lifecycle/` precedent of a neutral module layered beside the tracking core, and stdlib HTTP is sufficient for a loopback, token-authenticated, small-payload endpoint.

### D10. Verification reuses the existing qualification assets

- Posture/merge unit tests drive the reducer under `TestScheduler` virtual time (out-of-order, duplicate, orphan, stale-generation cases).
- TUI-only equivalence: `tests/unit/shared_tui_tracking/test_claude_2_1_296_qualification.py` and the gateway admission suites must pass unchanged with the channel disabled — this is the central gate.
- Recorded replay: extend the existing recorder format with an optional `hook_events.ndjson` sidecar, synthesized from labels, and replay existing campaign fixtures with and without it.
- Live smoke: managed Claude launches at 2.1.296 (and latest) covering normal turn, direct input, permission wait, compaction, stop/relaunch, and degraded states (collector killed, hooks disabled, untrusted workspace), run as a debug campaign under `context/campaigns/debug/`.

Rationale: reuses proven replay infrastructure instead of building a parallel harness; adds tests only for the materially new risks (merge, correlation, degradation).

### D11. Collector lifecycle follows the per-session gateway precedent

Collector start/stop is managed from `start_runtime_session`/`resume_runtime_session` and session stop, with `collector.json` (pid, port, generation; no token) as the liveness record — the same pattern as `gateway/run/gateway.pid`. Session cleanup removes `<session_root>/hook-observation/`; nothing else is touched.

## Risks / Trade-offs

- `--settings` not honored or HTTP hooks restricted at the 2.1.296 floor → verified live on 2026-10-19 (campaign iteration 1, floor S1 repeat): `--settings` is honored at 2.1.296, HTTP hooks deliver, and the managed-home layer behaves identically to 2.1.303. The channel degrades to `unavailable` and the session is unaffected, so the worst case remains no channel.
- `PostToolUse` frequency adds provider-side latency → D6's measurement gate; drop the event rather than engineering around it.
- File tailing lags the collector's in-memory state by reader poll time → bounded by D3's 0.5 s cycle; acceptable for v1 and measured in live smoke.
- A consumer reading a truncated mid-write line from `events.ndjson` → readers treat an unterminated final line as incomplete and retry next cycle; the collector writes single-line records under one writer.
- Token exposure through process environment listing on the host → loopback-only collector with a per-session token limits blast radius to the local host and session lifetime; documented as accepted local trust boundary.
- Duplicated posture across gateway and server consumers is harmless but could surface divergent conflict notes → conflict diagnostics are per-consumer local views; the spec only requires per-surface correctness.
- Workspace trust not seeded → channel reports `untrusted_workspace`; launch continues TUI-only (already the managed-launch behavior to seed trust).

## Migration Plan

No data or schema migration: all public additions are optional, and channel metadata is additive and session-local. Rollout is Phase 0 opt-in (D7). Rollback is unsetting the flag; sessions launched with the flag keep their observer until stopped, and a relaunch without it starts no collector and injects no settings. Default-on for managed Claude launches is a separate later change gated on the qualification evidence from D10.

## Open Questions

- Default values for startup grace and staleness thresholds (initially 15 s and 30 s; tunable after live evidence).
- Whether the gateway or houmao-server should suppress duplicate conflict notes when both track one session (cosmetic; defer to live observation).
