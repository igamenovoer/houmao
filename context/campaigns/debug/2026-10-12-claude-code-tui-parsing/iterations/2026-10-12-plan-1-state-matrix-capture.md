# Iteration 1: claude 2.1.296 state-matrix capture and detector gap analysis

Status: complete (2026-10-12). Question owner: [KQ-1](../key-questions/KQ-1-signal-survival.md); feasibility input to [KQ-2](../key-questions/KQ-2-transcript-oracle.md) via Arm C. Evidence: [session 1 lifecycle](../evidences/2026-10-12-session1-lifecycle-capture.md), [session 2 operator surfaces](../evidences/2026-10-12-session2-operator-surfaces-capture.md). Synthesis: [repair report](../reports/2026-10-12-claude-2-1-296-parsing-repair.md).

## Question

When claude 2.1.296 is driven through its public state matrix in tmux behind the OpenLux relay and recorded at 5 fps, which current-detector signals survive (per KQ-1 P1.1–P1.8), and what is the per-state mismatch catalog for the maintained `2.1.x` profile that 2.1.296 resolves to today (Arm A1) and, as control, the fallback detector (Arm A2)?

## Frozen Workload

| Component | Value |
| --- | --- |
| Host | This Linux dev host (linux-arm64); tmux; no hardware reservation needed |
| Tool under observation | `claude` 2.1.296 (`claude --version` → `2.1.296 (Claude Code)`, verified 2026-10-12); bun-compiled binary `~/.bun/install/global/node_modules/@anthropic-ai/claude-code-linux-arm64/claude`, SHA-256 recorded in the run manifest |
| Credential lane | `~/.local/bin/claude-openlux-0.5x` (OpenLux relay `https://api.openlux.ai`, key file `~/.local/bin/openlux-api-key`); real `~/.claude` config dir; no `CLAUDE_CONFIG_DIR` isolation |
| Model | `sonnet` via `--model sonnet` pass-through (user directive 2026-10-12: relay bills real money); verified in-TUI at session start (scenario op 0); any rejection or silent mismatch stops the run before driving |
| Source ground truth | None exists (claude is closed-source). Audit lane: string-grep on the installed binary, pre-campaign results recorded in `../debug-intent.md` Starting Evidence. Weaker than a source tree; reliability classifications account for this |
| Coding fixture (existing) | `tests/fixtures/test-projects/boltons` — vendored Boltons library, upstream revision `979fa9b613fa8c0a455ae16ea6f2ec91c11ecafe`, expected pytest collection 437; copied per session and git-baselined (`houmao-baseline` tag) per `prepare_boltons_project`. No new mini project is invented for this campaign |
| Prompt source (existing) | Reviewed operation catalog `scripts/demo/shared-tui-tracking-demo-pack/long-horizon/suite.json` (claude cells at lines 24, 183, 341, 504), shortened where the catalog is verbose (cost discipline); timing rules from the kimi campaign's UC-04-derived ready-window rule (≥2 samples after ≥max(2.0 s, 4× capture interval) idle) |
| Detector under test | Repo code as of campaign start. Arm A1: `ClaudeCodeSignalDetectorV2_1_X` — what 2.1.296 resolves to (`shared_tui_tracking/registry.py:122-129`). Arm A2: `FallbackClaudeDetector` via `--observed-version 0.0.0` override (control) |
| Recorder | `pixi run python -m tools.terminal_record start --mode active --tool claude --sample-interval-seconds 0.2` (5 fps, standing user directive); captures escape sequences (`capture-pane -p -e -S -`) |
| Run roots | `tmp/houmao-dev-tui-testing/<run-id>/` per `houmao-dev-tui-testing` artifact contract; campaign `evidences/` holds evidence documents, digests, and run-root references, not bulk copies |
| Driving | Tracker-blind scenario steps only (`send_text`, `send_key`, `wait_seconds`, documented `wait_for_pattern`); no `wait_for_ready`/`wait_for_active` |
| Credential hygiene | `openlux-api-key`, `~/.claude/.credentials.json`, and tokens are never read, printed, or copied. Transcript JSONL under `~/.claude/projects/` is read-only oracle input; artifacts quote event structure and timestamps, not full payloads |

## Predeclared Arms

| Arm | Input | Analysis | Output |
| --- | --- | --- | --- |
| A1 (status quo — today's resolution) | Frozen `pane_snapshots.ndjson` (ANSI-stripped view) | `tools.terminal_record analyze --observed-version 2.1.296` replay vs blind labels | Per-state field mismatches for the maintained 2.1.x profile |
| A2 (fallback control) | Same frozen snapshots | `tools.terminal_record analyze --observed-version 0.0.0` replay vs the same blind labels | Per-state field mismatches for the fallback; decides whether fallback removal (kimi/codex posture) loses anything real |
| B (escape sequences, audit only) | Same frozen snapshots, raw escape-preserving rows | Scripted audit for OSC 133 zone markers and OSC `9;4` progress sequences per labeled state | Presence/absence table by state |
| C (transcript oracle, feasibility only) | Session transcript JSONL under `~/.claude/projects/<boltons-copy-slug>/` written during the same sessions | Post-hoc event inventory with timestamps aligned to labeled spans | Event-coverage table for KQ-2 P2.1/P2.2/P2.3 |

One recording feeds Arms A1, A2, and B (the recorder already preserves escape sequences; `analyze` resolves the detector from the passed observed version). Arm C reuses provider-side artifacts of the same sessions; no extra capture is needed.

## Scenario (State Matrix)

Test cases will be specified in promptfoo-format configs under [2026-10-12-plan-1-state-matrix-capture/](2026-10-12-plan-1-state-matrix-capture/) (`session-1-lifecycle.yaml`, `session-2-operator-surfaces.yaml`, assertion contracts in `asserts/README.md`), created per the execution checklist before any launch; the YAML files are then the predeclared contract. Summary below.

Two recorded sessions, both running claude over a fresh copy of the existing Boltons fixture. Session 1 (launcher as-is: `--dangerously-skip-permissions`, `--model sonnet`): turn-lifecycle states. Session 2 (launcher environment lane minus the bypass flag; same relay, key, model, timeout): operator-interaction surfaces that bypass mode suppresses. Approval prompts in session 2 are answered with the rendered deny/refuse option to keep token spend minimal.

Session 1 operations (prompts adapted from `suite.json` claude cells, shortened for cost; timing per the ready-window rule):

0. **Model bootstrap (hard gate)**: launch `claude-openlux-0.5x --model sonnet`; verify the rendered model identity is sonnet (status line or `/model` picker display). If the relay rejects sonnet or silently substitutes another model, stop, record the failure, and consult the user before any further spend.
1. Cold start in the untrusted Boltons copy — capture startup rendering, any trust prompt (if rendered, select trust as a documented operator decision), tips/update notices; settle to the composer.
2. Settled idle — placeholder composer, footer/statusline; hold per the ready-window rule (≥2 samples after ≥2.0 s idle at 5 fps).
3. Editing — type a read-only prompt without submitting, Backspace over a literal suffix, hold, then clear; capture ghost-suggestion and draft styling (P1.2).
4. Busy phases and success — submit a short terminal task (`Run pwd and git status --short. Do not edit files.`); capture spinner lines, the `esc to interrupt` footer, and whatever completion marker 2.1.296 renders (P1.4's verb-set candidate); settle to a ready window.
5. Tool + edit workflow — read `pairwise`/`windowed`, create one small test file, run its pytest; captures sustained tool activity and one multi-turn active→ready cycle. Kept shorter than the codex equivalent for cost.
6. Queue / pending input — submit a moderately long prompt, then while busy type and submit a short follow-up; capture 2.1.296's queued-follow-up rendering (P1.7); let it drain.
7. Interrupt — submit a moderately long prompt, wait one confirmed active frame, send `Escape` once; capture the interrupted surface (P1.5); settle past the gap rule.
8. Compaction (opportunistic) — `/compact`; capture the compaction surface if it renders.
9. `/model` picker — open and capture the picker surface; cancel with Esc (also cross-checks op 0's model identity).
10. Exit — close the tool; capture process/pane loss.

Session 2 operations (launcher env lane minus `--dangerously-skip-permissions`, trusted Boltons copy, `--model sonnet`, new campaign-designed minimal prompts):

1. Command approval — submit "Run `git status --short` with your shell tool, then stop"; capture the approval surface shape; deny.
2. Edit approval — submit "Create `docs/houmao-campaign-note.md` with one sentence, then stop"; capture the edit-approval surface; deny.
3. `/model` picker — capture; Esc cancel.
4. Trust prompt — only if session 1's bypass launch suppressed it: relaunch without bypass in a fresh untrusted copy and capture the trust surface.

Retry countdowns, overload/rate-limit errors, and auto-compaction are opportunistic in both sessions (they cannot be forced reliably, and inducing them wastes spend); absence is recorded as missing coverage, not fabricated.

Deviation noted, no spec action: `openspec/specs/claude-code-state-tracking-*/` and `scripts/explore/claude-code-state-tracking/state-model.md` encode pre-2.1.296-era behavior models and are used as read-only references only. Campaign evidence may refute parts of them; divergences are recorded in `../evidences/` and `../reports/`, and any spec or implementation change happens only after manual review — this campaign does not modify `openspec/`.

## Gates

Pass/fail criteria declared before execution:

- G1 Recording completeness: recorder `manifest.json` has `stopped_at_utc` + `stop_reason`; `pane_snapshots.ndjson` and `input_events.ndjson` exist; `frozen-evidence.json` records SHA-256, byte size, and row counts for every bound file. FAIL → new attempt, preserve this one.
- G2 State coverage: every non-opportunistic state in the scenario has ≥1 contiguous labeled span of ≥2 samples (≥0.4 s at 5 fps). Missing states are declared as coverage gaps in the evidence doc; the iteration may still pass with named gaps.
- G3 Blind-label integrity: `labels.json` complete (every source sample labeled, all eight public fields, no overlaps) and `labels-manifest.json` frozen before any `analyze` or detector inspection. Any breach → labels discarded and re-authored from the raw recording.
- G4 Replay execution, both arms: `analyze --observed-version 2.1.296` and `analyze --observed-version 0.0.0` each complete on both sessions and emit `parser_observed.ndjson` + `state_observed.ndjson`; detector identity recorded per arm (`claude_code`/`2.1.x` vs `claude_code`/`fallback`).
- G5 Taint: `run_tainted` and all taint reasons recorded; a tainted run is reported as tainted, never silently treated as clean.
- G6 Unattended discipline: any unexpected confirmation prompt in session 1 (beyond the planned trust decision in op 1) marks that span failed per the TUI-testing skill rule; the span is excluded from pass claims.
- G7 Cost and model discipline: session 1 op 0 verifies sonnet before any driving; total relay spend is bounded by the two planned sessions with shortened prompts; any model substitution, unexpected third session, or retry storm is recorded as a cost deviation in the evidence doc with the cause. The key file is never read or printed (verified by checklist inspection, not by content).

## Measurements and Decision Rules

Measurements:

1. Per-sample agreement on the two user-facing booleans first (`surface_accepting_input`, `surface_ready_posture`), grouped by labeled state, reported separately for Arm A1 and Arm A2. Then the remaining six public tracked-state fields as diagnostic detail, grouped the same way.
2. Signal survival table per KQ-1 proposition: for every hardcoded assumption in `apps/claude_code/` (prompt anchor and composer rules, ghost-suggestion style codes, spinner/footer activity family, completion-marker needle, interruption text, color-246 failure heuristic, queued-preview structure, advisory needles) record: observed on 2.1.296 surface? detector behaved as designed? citing source sample IDs. For P1.4 additionally: which verb rendered, and whether the verb-set pattern would have caught it.
3. Arm B audit: count of samples containing OSC 133 / OSC `9;4` sequences, cross-tabulated by labeled state.
4. Arm C inventory: transcript event types present, timestamp alignment quality against labeled spans (feasibility input for KQ-2, not a pass/fail metric).

Decision rules (predeclared):

- A signal is **surviving** if it fires correctly on ≥95% of its state's labeled samples and on <5% of other samples.
- A signal is **broken** if it fires on <50% of its state's labeled samples, or fires on ≥5% of samples of an unrelated state.
- Otherwise **degraded**. Unreached states (coverage gap) leave their signals **unresolved**, explicitly.
- Boolean priority: false-ready and sustained false-busy errors on the two user-facing booleans outrank all per-state cosmetic mismatches; the iteration's headline metrics are the two boolean agreement rates per arm.
- Interference-only rule: claude-internal states beyond the public model (todo lists, Task/subagent activity, MCP boot, compaction) are scored only on whether the public fields stay correct in their presence; failure to name the internal state is never counted as a mismatch.
- Iteration disposition: KQ-1 propositions are marked confirmed/refuted per the survival table; the A1-vs-A2 comparison plus the survival table decides whether the repair is a patch of the 2.1.x family or a new 2.1.296-qualified family; the mismatch catalog is the primary input to the later repair proposal. Registry-posture disposition (floor vs interval, fallback removal) follows the kimi/codex precedent unless evidence shows the fallback earns its keep.

## Execution Checklist

- [x] Freeze this plan, KQ-1 propositions, arms, gates, decision rules (this document is the predeclaration)
- [x] Create fresh run roots under `tmp/houmao-dev-tui-testing/` (one per session; never reuse a non-empty root)
- [x] Prepare one Boltons working copy per session from `tests/fixtures/test-projects/boltons` (copy, `houmao-baseline` git baseline, 437-test collection preflight per `prepare_boltons_project`); record source and copy digests
- [x] Create the promptfoo-format case specs in `2026-10-12-plan-1-state-matrix-capture/` and expand them into runner inputs per the codex campaign's contracts
- [x] Record exact preconditions: `claude --version`, SHA-256 of the claude binary, launcher script SHA-256, key file existence (not content), relay reachability
- [x] Session 1: launch `claude-openlux-0.5x --model sonnet` in tmux on the untrusted Boltons copy; run op 0 model verification (hard stop on mismatch); start 5 fps active recording before the first driving operation
- [x] Drive session 1 operations 1–10 with tracker-blind steps; log operation timings
- [x] Stop recording; verify G1; freeze digests into `capture/frozen-evidence.json`
- [x] Session 2: replicate the launcher env lane minus `--dangerously-skip-permissions`, `--model sonnet`, fresh untrusted Boltons copy; record + drive operations 1–4; freeze (attempt 001 exposed auto mode; attempt 002 added the ask-rule overlay — see Corrections)
- [x] Author blind ground truth from raw recordings only (G3); freeze `labels-manifest.json` (all three runs)
- [x] Run Arm A1 replay (`analyze --observed-version 2.1.296`) and Arm A2 replay (`analyze --observed-version 0.0.0`) on all sessions; verify G4
- [x] Run Arm B escape-sequence audit script over all snapshot streams
- [x] Run Arm C transcript inventory on the sessions' JSONL files under `~/.claude/projects/` (read-only; structure and timestamps only)
- [x] Score measurements against decision rules; fill the signal survival table
- [x] Write evidence docs under `../evidences/` (session 1, session 2), update KQ-1 answer, KQ-2 answer, and `../debug-intent.md` status
- [x] Record relay spend deviation if any (G7); clean up credential-adjacent temp material per the artifact contract; record cleanup status (mangled-path write from attempt 001 removed; `/tmp` markers removed; probe sessions killed)

## Results (added after completion, 2026-10-12)

Gates: G1, G3, G4, G5 passed on all three frozen runs (session 1: 1563 samples; session 2 attempt 002: 1104; session 2 attempt 001: 1864). G2 passed with declared gaps: session 1 compaction (the `/compact` op typed onto the restored post-abort draft and submitted a mangled prompt; driver composition bug, recorded) and tui_down (double C-c at 1 s spacing did not exit); attempt 001's approval_modal spans (auto mode never renders dialogs — that is its evidence value). G6: no unexpected confirmation prompts in session 1 (the planned trust decision excepted). G7: sonnet verified in-TUI at both session starts (banner `Sonnet 5.5`); one corrective re-run (002) plus one zero-prompt live probe were the only extra spend, both recorded in Corrections.

Headline measurements (booleans, per-sample vs blind labels; A1 = maintained 2.1.x, A2 = fallback): session 1 — A1 accepting 0.9584 / ready_posture 0.4875 (50 false-ready: the trust modal's `❯`-option lines); session 2-002 — accepting 0.2355 / ready_posture 0.1667 (843 false-ready across the modal dwells); session 2-001 — accepting 0.9657 / ready_posture 0.4920. A1 and A2 agree within 0.04 on every field — the fallback earns nothing.

Disposition: KQ-1 resolved (survival table in its answer); KQ-2 answered (transcript oracle confirmed, ≤0.21 s seam alignment). Repair = patch the 2.1.x skeleton (modal shield first, verb-set dock, footer-primary busy, queue hint needle, temporal silent-abort channel); registry posture mirrors kimi/codex (floor at 2.1.296, no fallback). Full fix list: [repair report](../reports/2026-10-12-claude-2-1-296-parsing-repair.md).

## Post-Repair Candidate Qualification (added 2026-10-13)

The monkey-patched candidate detector (`scripts/explore/claude-code-tui-parsing/campaign_lib/patches.py`, replay tag `candidate-2.1.296`) implements the repair report's fix list plus two tracker-level findings surfaced during qualification (visible-draft outcome preservation, settle-identity signature projection — items 8-9 in the report's fix list). Per-sample agreement against the frozen labels (re-frozen after the 2026-10-13 boundary corrections):

| Session | accepting_input | ready_posture | false-ready | false-busy | turn_phase | pending | editing | last_turn_result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| s1 lifecycle (1563) | 1.0000 | 1.0000 | 0 | 0 | 1.0000 | 1.0000 | 0.9994 | 0.9859 |
| s2-002 operator (1104) | 1.0000 | 1.0000 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| s2-001 auto mode (1864) | 1.0000 | 0.9995 | 0 | 1 | 0.9995 | 1.0000 | 0.9989 | 0.9909 |

All residual mismatches are the two documented pipeline-semantics classes (settle-timer heads, submit-frame event ordering; see Corrections). Baselines against the corrected labels are unchanged at the headline precision (s1 0.9584/0.4875, s2-002 0.2355/0.1667, s2-001 0.9657/0.4920). Proposed qualification-gate thresholds for the integration change (codex-style, on the two booleans): s1 ≥ 0.999, s2-002 = 1.0, s2-001 ≥ 0.999.

## Corrections

- 2026-10-12 (pre-execution recon, not evidence): live ad-hoc launch of `claude-openlux-0.5x --model sonnet` in a scratch tmux pane established four plan inputs. (a) The trust dialog (`Quick safety check: Is this a project you created or one you trust?`) renders for an untrusted workdir **even under `--dangerously-skip-permissions`**; its default selection is `No, exit`, so the trust op is `Down` then `Enter` (never a bare `Enter`). Both session YAMLs handle it deterministically, superseding the plan text that assumed session 2 could be "trusted" in advance and session 1 might skip it. (b) Model bootstrap: after trust, the banner renders `Claude Code v2.1.296` / `Sonnet 5.5 · API Usage Billing`, confirming the relay resolves `--model sonnet` to Sonnet 5.5; the gate needle is the literal `Sonnet`. (c) The idle composer is boxed (`─` rules) with placeholder shape `Try "fix typecheck errors"` and posture footer `⏵⏵ bypass permissions on (shift+tab to cycle) · ← for agents`; the session-1 composer wait needles on `bypass permissions on` because `? for shortcuts` is not the settled idle footer in this build. (d) Session 2's composer wait cannot use the bypass footer; it waits on dialog absence plus the `❯` token instead.
- 2026-10-12 (pre-execution): recorded preconditions per the checklist — `claude --version` → `2.1.296 (Claude Code)`; binary SHA-256 `f1f6e96e0d8342b9dbf41d7e88255397a6a52ce3d8736ad6a4c6b59c9b62fefa` (256434168 bytes); launcher SHA-256 `11eb143781ebc14943b51e6af68dab98dbe98622ef4dfc07077fe5eeb5f63a7a`; key file existence `yes`; tmux 3.4; recorded 2026-10-12T13:47:16Z.
- 2026-10-12 (pre-execution): runner hardened with a per-op `abort_on_failure` flag so the model-verification op is a true hard stop (plan G7) instead of a recorded-but-continued leg.
- 2026-10-12 (session 2 attempt 001, `HMDEV-claude-20261012T140836`, frozen and preserved): Claude 2.1.296's default permission mode is **auto mode** — startup banner block "Auto mode is now Claude Code's default permission mode…", footer `⏵⏵ auto mode on (shift+tab to cycle)`. Auto mode auto-approved both approval-bait legs (`touch /tmp/…` shell write, `Write` file creation); `Do you want to proceed?` never rendered (both 180 s waits timed out, recorded as leg failures, run otherwise clean). Binary audit confirms the 2.1.296 mode cycle labels are only `auto mode on` / `plan mode on` / `bypass permissions on` — there is no ask-everything mode to switch to. A post-freeze live probe on the attempt-001 workdir validated the deterministic correction: a project `.claude/settings.json` with `{"permissions": {"ask": ["Bash(touch:*)", "Write"]}}` forces the classic dialog even under auto mode, rendering a boxed `Bash command` panel with `Ask rule Bash(touch:*) overrides auto mode for this command.`, `Do you want to proceed?`, options `❯ 1. Yes / 2. No`, footer `Esc to cancel · Tab to amend`. Attempt 002 adds a `workdir_overlay` provider-config key (runner support added) writing that settings file before launch; attempt 001 remains preserved as auto-mode evidence (startup banner, auto-mode footer, model picker) with its approval coverage gap superseded by 002.
- 2026-10-13 (post-repair label boundary corrections; labels re-frozen before the candidate replay): candidate design inspection of raw frames found blind-label boundaries that contradict unambiguous surface facts. Corrected in `author_labels.py` with per-row notes: (a) session 1 picker span starts at s001511 (the picker is fully rendered, not "materializing") and ends at s001524 (picker gone at s001525), with s001525-s001532 labeled `active` — **the preempted turn resumes streaming after the picker closes** (spinner + `esc to interrupt` footer) until the queued `/model` interruption lands at s001533, superseding the "picker preempts the turn" reading; (b) session 1 draft leg boundaries move to the composer evidence (editing s000067-s000092, ready s000093-s000097); (c) session 1's s000512-s000513 `editing_success` span dissolves into `ready_success` (composer verifiably empty; the write prompt renders only at submission); (d) session 2-002 editing span starts at s000067 (placeholder still renders at s000066); (e) session 2-001 gains an editing frame at s000066 (full command draft already in the composer). The baseline headline numbers are unchanged at 4-decimal precision.
- 2026-10-13 (post-repair semantics documented, labels unchanged): two residual mismatch classes are pipeline semantics, not detector error. (a) Success settle heads: `last_turn_result=success` latches only after the tracker's 1.0 s settle timer (5 samples at 5 fps) while labels count success from the dock frame — 20 samples in session 1, 15 in session 2-001 (including two re-settle runs where the long dwell surface churned below the dock). (b) Submit frames (s000929, s001371, s000950, s001831): the Enter input event invalidates the prior outcome (`input_submitted`) while the pre-submit surface still renders, so the joint event+surface state reads `editing + none` for one sample; labels hold the surface-only view.
