# Design

## Context

See proposal.md for motivation and the campaign evidence. Current state: `registry.py` registers one kimi profile (`>=0.34.0`, qualification-pending) plus a 0.11-shaped fallback; the selector picks the compatible registration with the greatest minimum version and falls back silently when nothing matches. The campaign's repaired detector exists as a monkey-patched candidate in `scripts/explore/kimi-code-tui-parsing/campaign_lib/patches.py`, qualified on two blind-labeled 2.1.1 recordings (zero false-ready / zero false-busy; booleans 99.2-100%).

## Goals / Non-Goals

**Goals:**
- One maintained kimi profile gated at `>=2.1.1`; explicit unsupported-version error below the floor or on unparseable versions.
- Production detector carries the campaign's measured repairs.
- Parser covers the 2.1.1 modal surfaces (trust, question, goal, approvals).
- Fixtures and unit tests rebuilt from 2.1.1 evidence.

**Non-Goals:**
- No changes to claude_code or codex_tui profiles, intervals, or fallback behavior.
- No reducer state-machine rewrite (`session.py` interrupt priority stays; detectors feed it sanitized signals).
- No escape-sequence (OSC) parsing channel; the campaign's Arm B audit showed OSC 133 / `9;4` never survive tmux capture.
- No user-facing "newer than qualified" warning path.
- No regeneration of the full 20 fps maintained corpus in this change; static fixture refresh only.

## Decisions

### D1: Registry shape — one registration, explicit error below floor
`registry.py` kimi registrations become a single entry: minimum `(2, 1, 1)`, maximum `None`, factory `KimiCodeSignalDetectorV2_1_X`. The kimi fallback registration is removed and `FallbackKimiCodeSignalDetector` is deleted. `_select_best_registration` gains a floor-aware path: when an app has registrations but no compatible and no fallback one, `resolve()` raises a new `UnsupportedToolVersionError` carrying app id, observed version, and floor. Today that case returns `registrations[0]` (the floor profile itself), which would silently scrape with the wrong detector; the error is the honest cut the user asked for.

Call-site containment: tracker/session construction and the terminal-record `analyze` path let the error propagate to the initiating operation (CLI/API caller sees it). The server supervisor's poll loop catches it per session and marks that session's tracking errored, so one stale kimi install cannot crash tracking for other sessions.

Alternative considered: map below-floor kimi to the `unsupported_tool` fallback posture. Rejected because it fails silently into `unknown` states; the operator needs the upgrade signal, and the user explicitly chose a hard error.

### D2: Detector promotion — candidate v3 becomes `KimiCodeSignalDetectorV2_1_X`
The candidate code moves from `campaign_lib/patches.py` into `apps/kimi_code/profile.py`, replacing `KimiCodeSignalDetectorV0_34_PLUS` (deleted). Content: spinner-union busy evidence (moon frames directly; braille frames qualified by the 2.1.x label set `Thinking…`/`Working…` U+2026, `Retrying (N/M)`, `Compacting context…`, `Orchestrating…`, `… Agent Running (…)`); compaction bullet text; modal detection (approval headers unchanged, question dialog, goal-start prompt); rubric-aligned input acceptance (visible composer = accepting even while busy; modal = closed); stale-interrupt suppression (`interrupted` only when no concurrent spinner-union activity); queue-hint live-edge scoping. `activity_window_lines=4`, temporal growth off, matching the 0.34+ pacing.

The class carries `qualified_through_version = "2.1.1"` (code-side metadata, decision B). `DetectorProfileRegistration` gains the same optional field, surfaced in resolver payloads and profile notes for developers.

### D3: Modal spans report active-with-blocked
Detectors report modal surfaces as `active_evidence=True` with reason `modal_blocked` (plus the existing `ambiguous_interactive_surface`), yielding `turn_phase=active`, `ready_posture=no`, `accepting_input=no`. This formalizes the reducer-observed convention over the campaign ground truth's `unknown` (user decision C). Known side effect, accepted: the startup trust modal manufactures a synthetic blocked "turn" before the first prompt; dashboards see blocked-active, which is the safe admission answer (never ready).

Alternative considered: `turn_phase=unknown` on modals. Rejected by the user; `unknown` also weakens admission safety consumers that treat unknown as possibly-ready.

### D4: Parser covers 2.1.1 modals; preset version stops being a lie
`server/tui/parser.py`: startup needles gain `Trust this folder?`; `_kimi_state_fields` gains question-dialog and goal-start branches mapping to `awaiting_operator` / `modal`; `parser_preset_version` stops being hardcoded — the parse call receives the resolved detector version (analyze path threads `observed_version`; live path uses the session's resolved profile version). The recorder's `_parse_kimi_snapshot_payload` gets the same modal branches.

### D5: Reducer unchanged; detectors sanitize `interrupted`
`session.py:351` keeps interrupt-over-active priority. The kimi 2.1.x detector suppresses stale scrollback notices (`interrupted` only without concurrent activity), so the priority rule no longer converts notice persistence into false-ready. Other tools' detectors inherit the same obligation implicitly; codex/claude profiles already scope their interrupt evidence to bounded regions.

### D6: Tests and fixtures rebuilt from campaign evidence
`tests/fixtures/shared_tui_tracking/kimi_code/*.txt` slices are re-captured from the frozen campaign recordings (idle, editing, busy-thinking, busy-tool, approval, question dialog, trust modal, queue, interrupt-resume). Unit tests updated: registry floor/error cases, detector field expectations per fixture, parser modal cases. Qualification gate: a test replays both campaign sessions through production code and asserts zero false-ready / zero false-busy plus >=99% agreement on the two admission booleans against the frozen labels.

## Risks / Trade-offs

- Future kimi (2.2+) silently matches a detector qualified only on 2.1.1 → qualified-through metadata (D2) plus the campaign's debug-campaign methodology as the standing re-qualification path; the user accepted silent resolution (no user-facing warning).
- Modal-as-active may surprise dashboards that equate active with streaming → documented in the spec delta; blocked reason is carried in `active_reasons`.
- A long-running server with mixed kimi versions sees per-session tracking errors until operators upgrade → per-session containment (D1); error message names the floor.
- The campaign's 5 fps captures are debug-grade, not the 20 fps canonical corpus → fixtures are static slices (cadence-independent); full corpus regeneration is follow-up work under the retargeted corpus spec.

## Migration Plan

Deployers tracking kimi-code below 2.1.1 see an explicit unsupported-version error at tracker resolution after upgrading houmao. Migration is upgrading kimi-code to 2.1.1 or later; no data or state migration exists. Rollback is reverting the change; no persisted artifacts depend on it.

## Open Questions

None blocking. The goal-start prompt (`Approve CreateGoal?`) and swarm surfaces remain unreached by live capture; their patterns ship source-backed but are marked qualification-pending until a future capture exercises them.

## Scope Addition Recorded During Apply

The launch-side kimi floor moved with the tracking floor (`launch_policy/registry/kimi.yaml` strategies renamed to `kimi-unattended-2.1-plus` / `kimi-tui-unattended-2.1-plus`, `launch_plan.py`, `brain_builder.py`): the user directive cuts all kimi support below 2.1.1, and leaving managed launch at `>=0.34.0` would create a limbo where below-floor kimi launches but cannot be tracked, and would make the 5.2 docs sweep contradict the launch code.
