# Report: codex 0.162.x TUI parsing repair (iteration 1 synthesis)

Date: 2026-10-12. Campaign: [debug-intent](../debug-intent.md). Evidence: [session 1](../evidences/2026-10-12-session1-lifecycle-capture.md), [session 2](../evidences/2026-10-12-session2-operator-surfaces-capture.md). Answers: [KQ-1](../key-questions/KQ-1-signal-survival.md), [KQ-2](../key-questions/KQ-2-structured-channels.md).

## What Survived Testing

**Approach**: repaired text scraping on the 0.144.x detector skeleton (Arm A path), qualified by monkey-patched replay against blind labels — no production code touched. Escape-sequence channels carry nothing (zero OSC in 2344 samples). The rollout event stream is a viable offline oracle (KQ-2), not a TUI replacement.

**Candidate qualification** (both frozen sessions, 1907 + 437 samples, per-sample agreement with blind labels):

| Metric | A1 fallback (today) | A2 0.144.x override | Candidate 0.162.x |
| --- | --- | --- | --- |
| s1 `surface_accepting_input` | 0.973 | 0.973 | **0.9995** |
| s1 `surface_ready_posture` | 0.887 | 0.873 | **0.9984** |
| s1 false-ready / false-busy | 147 / 68 | 242 / 0 | **2 / 1** |
| s2 `surface_accepting_input` | 0.826 | 0.826 | **1.0000** |
| s2 `surface_ready_posture` | 0.764 | 0.815 | **1.0000** |
| s2 false-ready / false-busy | 68 / 22 | 68 / 0 | **0 / 0** |

Candidate residuals, all diagnostic-level (the two booleans stay correct): `last_turn_result` carry across a post-interrupt compaction (reducer resets to `none` — see Open Questions); `surface_pending_input` undetectable during the queued-echo collapse window (single-snapshot limitation, see below); 3 seam samples (trust-confirm transition, two 1-sample stream-growth pauses); turn-seam `last_turn_result` resets one sample early.

## The Fix List (integrated 2026-10-12 via `raise-codex-floor-0-162-1`)

**Status: integrated.** Every item below landed in the change; see the
Integration Outcome section for the qualification scores and the deltas taken
during integration.

Candidate implementation for reference: `scripts/explore/codex-tui-parsing/campaign_lib/patches.py` (monkey patch). Integration converts these repairs into owned code.

**`src/houmao/shared_tui_tracking/registry.py`** — mirror the kimi change: delete `CodexTuiSignalDetectorV0_116_X` / `V0_144_X` registrations and `FallbackCodexTuiSignalDetector`; register one codex_tui profile with `minimum_supported_version=(0,162,1)`, unbounded max, `qualified_through_version="0.162.1"`; codex below floor raises `UnsupportedToolVersionError`. The class skeleton (prompt-behavior variant, temporal knobs) is the 0.144.x family's — patch-vs-rebuild answer: **patch** (the 0.144.x base + these repairs).

**`apps/codex_tui/signals/activity.py`** — check the status-row regex *before* the assistant-response-line break in `detect_activity`. Today any status label outside the hardcoded bullet prefixes (`• Compacting context (Ns • esc to interrupt)`) is swallowed as prose; compaction read `ready` 88/88 samples.

**`apps/codex_tui/signals/interrupted.py`** — replace the legacy two-sentence needle with the 0.162 prefix `Conversation interrupted` (whitespace-normalized, live-edge scoped). Stale suppression stays: interrupt notice only counts when no status row is active.

**`apps/codex_tui/profile.py`** — `_CODEX_WORKED_PREFIX`: `─ Worked for ` → `Worked for ` (prefix dropped in 0.162; marker docks as `Worked for Ns • HH:MM`).

**`apps/codex_tui/signals/overlays.py`** — add 0.162.x modals: trust screen (`Trust this folder?` + `Trust and continue`; renders even under bypass for untrusted git-repo workdirs), list-selection popups by new footer `enter select · esc back` (the old footer needle is dead; titles still match), warnings screen (`Warnings · N of M · Startup` + `esc dismiss`), and `Would you like to send input to the existing terminal?` (source-backed, capture-unverified).

**`apps/codex_tui/profile.py` detect() semantics** (candidate `detect` shows the shape): modal or startup-splash ⇒ `accepting/editing/ready/pending = no`, active suppressed, `success_blocked`; composer absent (no `›` line at all, e.g. the `codex resume` exit surface) ⇒ blocked (`no`), not `unknown`; startup splash = placeholder composer with no footer model line (`· /` anchor) yet ⇒ blocked; stale-interrupt suppression (`interrupted and not active`).

**Temporal inference** (candidate `derive_temporal_hints`): 0.162 hides the status row while the final answer streams, so the 0.144 veto "assistant response visible ⇒ no hints" reads streaming as turn-over. Replace with dock-awareness: hints die once `Worked for` docks in the latest-turn region; growth while undocked with turn content ⇒ active; a ≤1 s status-row blink with no dock ⇒ active carry. The turn-content gate (assistant bullet or numbered-stream line in region) prevents startup/editing redraws from manufacturing false activity.

**Queue / pending input**: a mid-busy submitted follow-up renders as `› <text>` above the status row and is *steer-merged* into the running turn (single `Worked for`; the legacy `• Messages to be submitted…` / steer-text needles never fire). Detectable while the echo is visible (disambiguator: assistant prose above the echo = in-flight turn, versus a `Worked for` dock or interrupt notice = turn-starting echo). **Limitation**: once the echo collapses into `+ N lines (^t to expand)` (~27 s of our 33 s queue window), no surface signal remains — persistent pending state needs tracker-level memory (a prompt submitted while active ⇒ pending until dock), which is a design decision for integration, not a scraping fix.

**`terminal_record/service.py`** — codex analyze flows through `ShadowParserStack` + `replay_timeline`; the candidate patch qualifies end-to-end through this path unmodified (registry resolution drives it). No codex-analyze changes needed for the 8 public fields.

**`src/houmao/agents/launch_policy/registry/codex.yaml`** — strategy id `codex-unattended-0.116.x` is stale; `supported_versions: ">=0.140.0"` overclaims. Re-probe on 0.162.1 (the kimi-style live_probe note), align the floor (`>=0.162.1`) and strategy naming. Launch-relevant 0.162 findings: `-a untrusted` no longer exists (only `on-request`/`never`); trust screen appears under bypass in untrusted git dirs.

**Tests / fixtures** — promote the two frozen sessions into `tests/fixtures/shared_tui_tracking/codex/` (snapshots gzipped, labels, input events, manifest + provenance README) and add a qualification replay test mirroring `test_kimi_code_2_1_x_qualification.py` (candidate expectations: session 1 booleans ≥99.8%, session 2 100%). Rewrite `test_codex_prompt_behavior.py` / `test_codex_tui_session.py` around 0.162.1 fixtures; delete the two `stale_active_*` ANSI captures or re-derive them.

## Open Questions (not resolved by this iteration)

1. **Reducer carry**: should `last_turn_result=interrupted` persist across a compaction that follows the interrupt? Today the reducer resets to `none` when compaction activity reads as a new turn. GT says carry; decide at integration (affects no booleans).
2. **Pending-input collapse window**: accept the 27 s blind spot, or track submission events tracker-side? The campaign recommends tracker-side memory as the honest fix.
3. **Error/retry cells** (stream disconnect, context length, server errors): uncaptured — fault-injection iteration needed before those regexes can be re-qualified. The old inventory remains in place unqualified.
4. **Live app-server attach** (KQ-2 remainder): can a client stream lifecycle events from a running TUI session? If yes, an event-driven tracker variant becomes viable for houmao-launched sessions.
5. **Edits-form approval** (`…make the following edits?`) and permissions-grant surfaces: text captured nowhere yet; needles kept from source, unverified by capture.

## Integration Gate

Per the user directive (2026-10-12), nothing integrates until these artifacts are reviewed: this report, the two evidence docs, and the candidate patch. Suggested integration path after review: one change touching `shared_tui_tracking` (detector + registry floor), launch policy, and fixtures, with the qualification replay as the standing gate.

## Integration Outcome (2026-10-12)

**Integrated.** The fix list above landed as OpenSpec change
[`openspec/changes/archive/2026-10-12-raise-codex-floor-0-162-1/`](../../../../../openspec/changes/archive/2026-10-12-raise-codex-floor-0-162-1/proposal.md)
(single floor-gated `CodexTuiSignalDetectorV0_162_X` at `>=0.162.1`, launch
strategy `codex-unattended-0.162-plus`, `codex_app_server` blocked as
unmaintained, fixtures promoted to
`tests/fixtures/shared_tui_tracking/codex/qualification/`).

The production qualification gate
(`tests/unit/shared_tui_tracking/test_codex_0_162_x_qualification.py`) replays
both frozen sessions through `analyze_terminal_record` and reproduces the
candidate's measured scores exactly: session 1 `0.9995` accepting / `0.9984`
ready (2 false-ready + 1 false-busy diagnostic-level residuals), session 2
`1.0000` / `1.0000`.

Integration-time decisions beyond the candidate patch (all covered by the
change's design):

- Queued echoes report pending input and active-turn evidence without the
  candidate's active-evidence precondition; the disambiguator gained a
  below-echo dock/interrupt check so settled surfaces beside a draft never
  read as queued. Qualification scores are unchanged.
- Compaction status rows carry a distinct `compaction_status` active reason
  (instead of `status_row`); the shared reducer treats maintenance-only
  activity as non-authoritative for newer-turn invalidation and success
  settlement, so `last_turn_result=interrupted` survives a post-interrupt
  compaction (resolves Open Question 1 with the carry answer).
- Error/retry needles were re-derived from 0.162.x source
  (`extern/orphan/codex`) with source references in code notes; the
  server-error and unknown-parameter families stay qualification-pending
  until a fault-injection iteration (Open Question 3, still open as a
  follow-up).
- The status-row blink carry does not fire over a visible draft (prompt
  edits are prompt-originated evidence, not a hidden status row).
- The two `stale_active_*` ANSI captures were deleted: settled 0.162.1 frames
  never retain status rows in scrollback (codex redraws them away), so the
  captures could not be re-derived from evidence; the live-edge protection
  they covered stays tested by the response-supersedes case.
- `scripts/explore/codex-tui-parsing/campaign_lib/patches.py` is preserved as
  campaign evidence; it monkey-patches the retired pre-change modules and no
  longer runs against production (the candidate is the production detector).

Follow-ups recorded on the change's tasks: fault-injection qualification of
error/retry surfaces, tracker-side pending-input memory for the queued-echo
collapse window (Open Question 2), live app-server event-attach investigation
(Open Question 4), and edits-form/permissions-grant capture (Open Question 5).
