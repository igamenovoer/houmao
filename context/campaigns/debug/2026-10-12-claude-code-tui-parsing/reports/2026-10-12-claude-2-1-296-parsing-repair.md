# Report: claude 2.1.296 parsing repair — findings and fix list

Date: 2026-10-12. Campaign: [2026-10-12-claude-code-tui-parsing](../debug-intent.md). Inputs: [KQ-1](../key-questions/KQ-1-signal-survival.md) (resolved), [KQ-2](../key-questions/KQ-2-transcript-oracle.md) (answered), [session 1 evidence](../evidences/2026-10-12-session1-lifecycle-capture.md), [session 2 evidence](../evidences/2026-10-12-session2-operator-surfaces-capture.md). Status: awaiting manual review before any integration (no production code changed by the campaign).

## Verdict

The maintained `ClaudeCodeSignalDetectorV2_1_X` (qualified around 2.1.81) is stale on 2.1.296 in exactly the load-bearing places, and the staleness is invisible because 2.1.296 sits inside the registered [2.1.0, 2.2.0) interval. On the two user-facing booleans the current detector scores:

| Session | accepting_input | ready_posture | false-ready | false-busy |
| --- | --- | --- | --- | --- |
| s1 lifecycle (1563 samples) | 0.9584 | 0.4875 | 50 | 7 |
| s2-002 operator surfaces (1104) | 0.2355 | 0.1667 | 843 | 0 |
| s2-001 auto mode (1864) | 0.9657 | 0.4920 | 63 | 1 |

The fallback detector scores identically (±0.04 on every field) — it earns nothing, and the kimi/codex registry posture (floor at the qualified version, no fallback, `UnsupportedToolVersionError` below floor) is the correct disposition for claude too.

Repair is a patch of the existing 2.1.x skeleton, not a rebuild: the composer structure, ghost styling, prompt anchor, footer busy suffix, and interrupt line all survive; what broke is the completion marker, the queued-input surface, the spinner variants, the silent Esc abort, and the total absence of modal masking.

## Confirmed 2.1.296 Surface Facts (evidence-backed)

1. Composer stays boxed (`─` rules, `❯` anchor) with `❯\xa0` NBSP payloads; placeholder tip text (`Try "…"`) renders only on the fresh composer; empty post-turn composers are bare `❯` with ghost styling (fg 231 / bg 237).
2. Busy: footer gains `· esc to interrupt ·…` (741/744, 76/76, zero false fires — the primary busy signal). Spinner: `<glyph> <Gerund>…` with glyph cycle `✽ * · ✻ ✢`, randomized gerund family (`Calculating`, `Ebbing`, `Blanching`, `Cerebrating`), optional `(Ns · ↓ N tokens)` suffix, hidden while the answer streams.
3. Completion dock: `✻ <Verb> for <dur> · done <time>` with per-turn verb from `["Baked","Brewed","Churned","Cogitated","Cooked","Crunched","Sautéed","Worked"]` (binary audit + 5 distinct verbs captured); durations are `Nm Ns` (`1m 27s`), not bare `\d+[smh]`. Denied turns dock too (approval denials show a verb dock). The dock persists in scrollback — unscoped matching false-fires (740 in session 1).
4. Queue: composer placeholder becomes `Press up to edit queued messages`; the submitted follow-up then echoes into the transcript as a `❯` user block and merges into the running turn (steer-merge, single dock).
5. Interrupt: three distinct behaviors — (a) Esc mid-turn: silent abort, prompt restored into the composer as a draft, **no** transcript line; (b) C-c/approval-denial/slash-preemption: `⎿ Interrupted · What should Claude do instead?` renders (indented 2 spaces, NBSP after ⎿) and persists in scrollback; (c) queued `/model` preempts a streaming turn (ends it as interrupted).
6. Modals (all render `❯`-option lines that false-fire the bare prompt token): trust dialog `Quick safety check` / `Yes, I trust this folder` (default selection is `No, exit`; renders even under `--dangerously-skip-permissions`); `Select model` picker (numbered entries, `❯ 5. Sonnet ✔`, `… +8 models`); approvals `Do you want to proceed?` (command) and `Do you want to create <name>?` (edit) with boxed `╌`-rule panels and `Esc to cancel · Tab to amend` footers.
7. Auto mode is 2.1.296's default permission mode (startup banner + `⏵⏵ auto mode on` footer); it auto-approves low-risk tool calls with **no dialog** (`⎿ Allowed by auto mode classifier` on the write). No ask-everything mode exists in the cycle (binary labels: `auto`, `plan`, `bypass` only). Deterministic approval prompts require `permissions.ask` rules.
8. Exit: double C-c at 1 s spacing did not exit; `Press Ctrl-C again to exit` is a transient hint (appears after the second press in our timing).
9. Escape sequences: zero OSC 133 / OSC `9;4` in 4531 samples — no state-bearing channels (same as codex).
10. Transcript oracle: `~/.claude/projects/*.jsonl` carries `user` / `assistant` / `system.turn_duration` / `queue-operation` records aligning to labeled seams within 0.11–0.21 s — a viable post-hoc oracle for future qualification (KQ-2).

## Fix List (for the integration change, post-review)

Detector (`src/houmao/shared_tui_tracking/apps/claude_code/`):

1. **Modal shield first**: detect modal surfaces (trust dialog, picker, approval panels, and future `Do you want to …` / `Esc to cancel · Tab to amend` shapes) before prompt classification; modals force accepting/editing/ready/pending = no with activity suppressed. This fixes 843/843 of session 2's false-ready samples and 50/50 of session 1's.
2. **Completion marker**: replace `Worked for \d+[smh]` with a dock-scoped verb-set match — `✻` prefix + the eight-verb alternation + `for (\d+m )?\d+s` — scoped to the live edge or the latest turn region, never full-scrollback.
3. **Busy detection**: keep the `esc to interrupt` footer suffix as primary; fix the spinner regex to make the `(…)` suffix optional and tolerate trailing whitespace; treat the spinner's absence during answer streaming as expected (rely on the footer).
4. **Queued input**: replace the ghost-echo-cell structure with the composer placeholder needle `Press up to edit queued messages` (bounded token, per the needle-style rule).
5. **Interrupt**: widen the region status-line needle: `⎿ Interrupted · What should Claude do instead?` (C-c/preemption) **and** `⎿ User rejected …` (approval denial) both render indented with an NBSP after `⎿`; match the stripped line by essential token (`^⎿\s+(Interrupted|User rejected)\b`), dropping the full-sentence anchor. Add the temporal channel: active → idle-footered transition with no modal, no interrupt line, and no fresh region dock = silent abort (a dock is fresh only if it was not visible during the active frames — the aborted turn's echo can scroll off, leaving the *previous* turn's dock inside the region). The restored draft makes the composer look edited, which is correct: `editing_input=yes` after an Esc abort. Two companion temporal rules: slash-menu blink carry (the autocomplete hides the busy footer and spinner for a frame — activity within 1 s means still active), and modal-dismissal restore (a modal opened from an idle interrupted surface restores `interrupted` on dismissal; the `/model` echo re-anchors the region and hides the line from the static needle).
6. **ready_posture semantics**: the 2.1.x profile never asserts `no` during busy (it returns `unknown`), which is why ready_posture agreement is 0.49 even though accepting_input is 0.96. The repaired detector should assert `no` when the busy footer/spinner is present and `yes` only at an unmasked usable composer — matching the operational boolean contract.
7. **Registry**: mirror kimi/codex — single registration with floor at the qualified version (`>=2.1.296`, `qualified_through_version="2.1.296"`), delete `FallbackClaudeDetector`, raise `UnsupportedToolVersionError` below floor.
8. **Tracker: visible-draft invalidation** (`session.py`, found in candidate qualification): `_invalidate_stale_terminal_outcome_for_newer_turn_locked(reason="visible_draft")` clears a latched terminal outcome whenever a draft renders. 2.1.296 restores the aborted prompt into the composer on a silent abort, and labels hold the latched outcome while the operator types (`editing_interrupted` / `editing_success` spans). Skip invalidation for `visible_draft`; `active_signal` and `input_submitted` still clear. Without this, the interrupted latch survives exactly one frame on any restored-draft span.
9. **Tracker: settle-identity signature** (found in candidate qualification): `surface_signature` hashes the whole stripped surface, so volatile furniture churn (the tip line below the dock appearing/disappearing, transient hints, the effort indicator) triggers `success_invalidated`, and the consumed turn authority then blocks re-settling — a settled success silently reverts to `none` for the rest of the span (140 samples in session 1). Compute the settle-identity signature over state-bearing lines only (`❯`/`●`/`⎿`/`✻` anchors, box rules, mode footer). Also gate `success_candidate` off while the composer carries a draft (typing is not a settle surface).
10. **Launch policy** (`claude.yaml`): realign `supported_versions` with the qualified floor; note that auto mode (2.1.296 default) changes unattended behavior assumptions probed at 2.1.81 — approval-prompt expectations in houmao's claude launch contract need re-review against auto mode.

Fixtures and gates:

11. Promote the three frozen sessions into `tests/fixtures/shared_tui_tracking/claude/` (first claude corpus) with a qualification replay test mirroring the codex gate, thresholds from the qualified candidate's measured scores (s1 ≥ 0.999, s2-002 = 1.0, s2-001 ≥ 0.999 on the two booleans).
12. `scripts/explore/claude-code-tui-parsing/` stays as the campaign tooling; the candidate monkey-patch module (`campaign_lib/patches.py`) is the integration source of truth.

## Candidate Qualification (2026-10-13, post-repair pass)

The candidate (`campaign_lib/patches.py`, replay tag `candidate-2.1.296`) was replayed in-process through the maintained `analyze_terminal_record` path against all three frozen sessions, labels re-frozen after the boundary corrections recorded in the iteration plan. Per-sample agreement:

| Session | accepting_input | ready_posture | false-ready | false-busy | turn_phase | pending_input | editing_input | last_turn_result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| s1 lifecycle (1563) | 1.0000 | 1.0000 | 0 | 0 | 1.0000 | 1.0000 | 0.9994 | 0.9859 |
| s2-002 operator (1104) | 1.0000 | 1.0000 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| s2-001 auto mode (1864) | 1.0000 | 0.9995 | 0 | 1 | 0.9995 | 1.0000 | 0.9989 | 0.9909 |

Residual mismatches are the two documented pipeline-semantics classes only: success settle-timer heads (1.0 s settle = 5 samples per success span) and submit-frame event ordering (the Enter event clears the prior outcome one sample before the surface turns). Baselines against the corrected labels are unchanged at headline precision.

Follow-ups (declared, not this iteration):

- Error/retry surfaces (overload, rate limit, stream disconnect) — unreachable without relay faults; fault-injection iteration needed (P1.6 unresolved).
- Auto-compaction surface (`/compact` leg was mangled by the restored-draft collision) — recapture with a clean composer (clear the restored draft first).
- tui_down exit surface — re-drive with the hint-aware C-c timing (second press inside the hint window).
- The `/btw` side-question surface and `atis-latch` records — seen in transcripts/tips, not driven.

## Integration Outcome

(to be filled after manual review and integration, mirroring the codex campaign's outcome section)
