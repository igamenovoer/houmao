# Design

## Context

See proposal.md for motivation and the campaign evidence. Current state: `registry.py` registers three codex profiles (0.116.x bounded, 0.144.x bounded, and a versionless fallback); the selector falls back silently when nothing matches. The campaign's repaired detector exists as a monkey-patched candidate in `scripts/explore/codex-tui-parsing/campaign_lib/patches.py`, qualified on two blind-labeled 0.162.1 recordings (session 1: 0.9995 accepting / 0.9984 ready over 1907 samples; session 2: 1.0000 / 1.0000 over 437 samples; 2 false-ready + 1 false-busy + 3 seam samples total). `UnsupportedToolVersionError` and `qualified_through_version` already exist from the kimi 2.1.1 change, so the registry-side machinery is reused, not rebuilt.

## Goals / Non-Goals

**Goals:**
- One maintained codex profile gated at `>=0.162.1`; explicit unsupported-version error below the floor or on unparseable versions.
- Production detector carries the campaign's measured repairs.
- Launch-policy codex floor aligned with the tracking floor.
- Fixtures and unit tests rebuilt from the frozen 0.162.1 campaign evidence.

**Non-Goals:**
- No changes to claude_code or kimi_code profiles, intervals, or fallback behavior.
- No reducer state-machine rewrite (`session.py` priorities stay); one scoped exception: the maintenance-turn carry guard in D7.
- No escape-sequence (OSC) parsing channel; the campaign's Arm B audit showed zero OSC sequences survive tmux capture in 2344 samples.
- No user-facing "newer than qualified" warning path.
- No tracker-side pending-input memory in this change; the queued-echo collapse blind spot is documented, and the "visibly holds" pending-input contract stands (resolved during proposal review, 2026-10-12).
- No fault-injection qualification of error/retry surfaces (stream disconnect, context length); the legacy error regex inventory stays in place unqualified, unchanged by this change.
- No live app-server event attach (KQ-2 remainder stays open).

## Decisions

### D1: Registry shape — one registration, explicit error below floor
`registry.py` codex registrations become a single entry: minimum `(0, 162, 1)`, maximum `None`, factory `CodexTuiSignalDetectorV0_162_X` with `qualified_through_version="0.162.1"`. The 0.116.x and 0.144.x registrations and the codex fallback registration are removed; `CodexTuiSignalDetectorV0_116_X`, `CodexTuiSignalDetectorV0_144_X`, and `FallbackCodexTuiSignalDetector` are deleted. Below-floor or unparseable codex resolves through the existing `UnsupportedToolVersionError` floor path introduced for kimi; call-site containment (per-session error in the server supervisor, propagation to the initiating operation elsewhere) is inherited unchanged.

Alternative considered: keep the fallback for newer-than-qualified codex. Rejected because the floor-gated pattern is now the house rule for fast-moving CLIs (kimi precedent), and the fallback's silent scraping produced the exact false-ready drift this change fixes.

### D2: Detector promotion — candidate becomes `CodexTuiSignalDetectorV0_162_X`
The candidate code moves from `campaign_lib/patches.py` into owned code under `apps/codex_tui/`, keeping the 0.144.x family skeleton (prompt-behavior variant, temporal knobs) and applying the measured repairs:

- `signals/activity.py`: the status-row regex family is checked before the assistant-response-line break in `detect_activity`, so compaction and other maintained status labels count as busy instead of being swallowed as prose (measured: compaction read `ready` 88/88 samples before the repair).
- `signals/interrupted.py`: the interruption needle becomes the whitespace-normalized prefix `Conversation interrupted`, live-edge scoped; stale suppression stays (the notice counts only when no status-row activity is visible).
- `profile.py`: `_CODEX_WORKED_PREFIX` becomes `Worked for ` (0.162 dropped the `─` box-drawing prefix; the dock renders as `Worked for Ns • HH:MM`).
- `signals/overlays.py`: add the 0.162.x modal inventory — workspace-trust screen (`Trust this folder?` + `Trust and continue`), list-selection picker via the new footer `enter select · esc back`, startup warnings screen (`Warnings · N of M · Startup` + `esc dismiss`), and the send-input-to-terminal dialog (source-backed, capture-unverified, marked qualification-pending).
- `profile.py` detect() semantics: a mounted modal or the startup splash reports accepting/editing/ready/pending = no with active suppressed and success blocked; a surface with no composer line at all (the `codex resume` exit surface) reports blocked rather than unknown; the startup splash is recognized as the placeholder composer without the footer model line yet.
- Temporal inference (`derive_temporal_hints`): dock-aware — hints die once `Worked for` docks in the latest-turn region; growth while undocked with turn content counts as active; a status-row blink of about one second or less with no dock carries active; a turn-content gate (assistant bullet or numbered-stream line in the region) prevents startup/editing redraws from manufacturing activity.
- Pending input: the queued-echo needle (`› <text>` above the status row, disambiguated by in-flight turn content above it versus a `Worked for` dock or interrupt notice) reports pending input while visible. The legacy pending-section headers (`Messages to be submitted …`, `Queued follow-up inputs`) are removed — they never render in 0.162 (follow-ups steer-merge into the running turn).
- Needle style: source-backed surfaces (modal inventory, error/retry families) are recognized from bounded structure plus essential semantic tokens rather than exact full-sentence literals, extending the existing terminal-failure convention to the whole 0.162 inventory, so minor upstream rewording does not silently break detection.

The class carries `qualified_through_version = "0.162.1"` (code-side metadata).

### D3: Modal spans report blocked, codex-style
Unlike kimi's active-with-blocked convention, the codex profile keeps its existing convention: operator surfaces report blocked admission (accepting/editing/ready/pending = no) with active suppressed and success blocked, and the reducer does not manufacture a terminal result from an overlay. The campaign's labels confirmed this shape qualifies (session 2 booleans 1.0000/1.0000); the two admission booleans are the operator-facing contract and they behave identically across both conventions.

Alternative considered: adopt kimi's `turn_phase=active` + blocked reason for codex modals for cross-tool symmetry. Rejected: codex's existing reducer contract already treats overlays as posture-degrading without terminal manufacturing, the candidate qualified with that shape, and harmonizing conventions is cosmetic work that risks the measured scores.

### D4: Queued-echo collapse window stays a documented blind spot
Once a queued echo collapses into `+ N lines (^t to expand)` (~27 s of the campaign's 33 s queue window), no single-snapshot signal remains. This change ships the single-snapshot needle only and documents the limitation in the spec delta; persistent pending state across the collapse requires tracker-side submission memory (a prompt submitted while active implies pending until dock), which is a tracker-layer design decision deferred to a follow-up change.

Alternative considered: ship a tracker-side memory heuristic now. Rejected: it is a reducer change with its own false-pending risks, the campaign did not qualify it, and the user-facing booleans (ready/accepting) are unaffected.

### D5: Launch floor moves with the tracking floor
`launch_policy/registry/codex.yaml`: strategy id `codex-unattended-0.116.x` renamed to `codex-unattended-0.162-plus` with `supported_versions: ">=0.162.1"`; the live-probe evidence is re-run on 0.162.1 and the note updated. Launch-relevant 0.162 findings recorded in the campaign are folded into the strategy notes: the `-a untrusted` approval flag no longer exists (only `on-request`/`never`), and the trust screen renders under full bypass for untrusted git workdirs, so the runtime-owned trust preseed remains load-bearing. Any launch-plan or brain-builder references to the old strategy id or floor are updated, mirroring the kimi scope addition.

### D6: Tests and fixtures rebuilt from campaign evidence
The two frozen campaign sessions are promoted into `tests/fixtures/shared_tui_tracking/codex/` (gzipped snapshots, frozen labels, input events, manifest, provenance README naming the campaign run roots). A qualification test mirroring `test_kimi_code_2_1_x_qualification.py` replays both sessions through production replay and asserts session-1 booleans ≥99.8% and session-2 at 100% on `surface_accepting_input` and `surface_ready_posture`. `test_codex_prompt_behavior.py` and `test_codex_tui_session.py` are rewritten around 0.162.1 fixtures; the two stale `stale_active_*` ANSI captures are deleted or re-derived from the frozen sessions.

### D7: Maintenance turns carry the previous prompt-turn result
The reducer gains a scoped carve-out: provider maintenance activity that is not operator prompt work — concretely the codex context-compaction surface, tagged by the detector with a compaction active reason — neither counts as authoritative newer-turn evidence nor settles success over a prior terminal outcome. `last_turn_result=interrupted` therefore survives a post-interrupt compaction, matching the campaign's operator-audited labels. Prompt-originated evidence (explicit input submission, visible non-placeholder draft) keeps the existing invalidation behavior. This decided during proposal review (2026-10-12) against the alternatives of re-labeling the ground truth to excuse the reset, or deferring a known-wrong public diagnostic.

Alternative considered: keep the reducer untouched and re-label the compaction span `none` (kimi-D5-style purity). Rejected: the field's meaning is "the last prompt turn's result," compaction is not a prompt turn, and the frozen labels already encode the operator's judgment — adjusting labels to excuse the code inverts the qualification relationship.

### D8: `codex_app_server` is blocked as unmaintained
The deprecation window recorded in `brain-launch-runtime` closes: the backend has not been qualified against current codex releases and is declared unmaintained (user directive during proposal review, 2026-10-12). Launch requests and retained manifests naming `codex_app_server` raise an explicit unmaintained-backend error before provider start, naming the maintained alternatives (`codex_headless`, `local_interactive`), following the `cao_rest` retirement pattern — the module stays in the tree as dead code, and no runtime path silently honors it. The `codex.yaml` strategy drops the backend from its backends list. The KQ-2 event-attach follow-up stays deferred; if it ever lands, it arrives as a new maintained backend rather than a resurrection of this one.

Alternative considered: keep honoring explicit `codex_app_server` overrides. Rejected by the user: an untested backend presents unmaintained behavior as supported, and the failure mode (a session that starts but behaves wrong) is worse than a loud launch-time rejection.

## Risks / Trade-offs

- Future codex (0.163+) silently matches a detector qualified only on 0.162.1 → qualified-through metadata (D2) plus the debug-campaign methodology as the standing re-qualification path; the user accepted silent resolution.
- Unqualified surfaces remain: edits-form approval (`…make the following edits?`), permissions-grant, error/retry cells, and delegation frames were not captured → needles ship source-backed and marked qualification-pending; a fault-injection iteration is the follow-up.
- The queued-echo collapse blind spot means `pending_input` can read `no` while a follow-up is genuinely queued → documented in the spec and report; tracker-side memory is the recommended follow-up (D4).
- A long-running server with mixed codex versions sees per-session tracking errors until operators upgrade → per-session containment inherited from the kimi floor path; the error message names the floor.

## Migration Plan

Deployers tracking codex below 0.162.1 see an explicit unsupported-version error at tracker resolution after upgrading houmao; migration is upgrading codex to 0.162.1 or later. Callers launching `backend=codex_app_server` see an explicit unmaintained-backend error; migration is switching to `codex_headless` (structured non-interactive) or `local_interactive` (tracked TUI). No data or state migration exists. Rollback is reverting the change; no persisted artifacts depend on it.

## Open Questions

From the campaign report; Q1 was resolved during proposal review on 2026-10-12:

1. ~~Tracker-side pending-input memory (D4)~~ — **Resolved: deferred.** The documented contract for `surface_pending_input` is "provider TUI *visibly holds* submitted input" (`docs/reference/tui-tracking/state-model.md:165`), so reading `no` during the queued-echo fold is contract-conformant; the fold likely coincides with the steer-merge consuming the input. Reopening this would be a contract change, not a scraping fix; it stays a workflow follow-up.
2. ~~Should `last_turn_result=interrupted` persist across a compaction that follows the interrupt?~~ — **Resolved: carry.** Maintenance turns neither reset nor settle over the previous prompt-turn result (D7); the shared reducer gains a scoped guard and the spec delta records it under `official-tui-state-tracking`.
3. ~~Error/retry surface qualification needs a fault-injection iteration before those regexes can be re-qualified.~~ — **Resolved: source-backed now, simulated later.** The error/retry/degraded needle inventory (stream disconnect, context length, server errors) is re-derived from the 0.162.x source under `extern/orphan/codex` in this change and marked qualification-pending; the fault-injection capture iteration that qualifies them stays a follow-up.
4. ~~Edits-form approval and permissions-grant surfaces were never captured.~~ — **Resolved: source-backed now, captured later, pattern-based.** Their needles ship from 0.162.x source inspection marked qualification-pending, recognized by bounded structure plus essential semantic tokens rather than exact literals (needle-style rule in D2); an interactive-session capture iteration qualifies them later.
5. ~~Live app-server attach (event-driven tracker variant) remains unexplored.~~ — **Resolved: deferred, and the existing lane is frozen.** The TUI-session event-attach probe stays a follow-up; separately, the unmaintained `codex_app_server` headless backend is blocked at launch in this change (D8), since it has not been qualified for a long time.
