# Iteration 1: codex 0.162.1 state-matrix capture and detector gap analysis

Status: complete (2026-10-12). Question owner: [KQ-1](../key-questions/KQ-1-signal-survival.md); feasibility input to [KQ-2](../key-questions/KQ-2-structured-channels.md) via Arm C. Evidence: [session 1 lifecycle](../evidences/2026-10-12-session1-lifecycle-capture.md), [session 2 operator surfaces](../evidences/2026-10-12-session2-operator-surfaces-capture.md). Synthesis: [repair report](../reports/2026-10-12-codex-0-162-x-parsing-repair.md).

## Question

When codex-cli 0.162.1 is driven through its public state matrix in tmux and recorded at 5 fps, which current-detector signals survive (per KQ-1 P1.1–P1.7), and what is the per-state mismatch catalog for each candidate detector — the fallback that 0.162.1 resolves to today (Arm A1) and the newest maintained profile, 0.144.x, replayed via observed-version override (Arm A2)?

## Frozen Workload

| Component | Value |
| --- | --- |
| Host | This Linux dev host; tmux; no hardware reservation needed |
| Tool under observation | `codex` 0.162.1 (`codex --version` → codex-cli 0.162.1, verified 2026-10-12) |
| Codex configuration | `CODEX_HOME=/data/huangzhe/code/houmao/.codex` (ChatGPT login; `codex login status` verified 2026-10-12), model `gpt-6.1-sol`, `model_reasoning_effort=medium` (user directive 2026-10-12); workdir trust already granted for the repo, fresh Boltons copies are untrusted |
| Source ground truth | `extern/orphan/codex` @ 322bbf4 (2026-10-10 checkout, read-only) |
| Coding fixture (existing) | `tests/fixtures/test-projects/boltons` — vendored Boltons library, upstream revision `979fa9b613fa8c0a455ae16ea6f2ec91c11ecafe`, expected pytest collection 437; copied per session and git-baselined (`houmao-baseline` tag) per `prepare_boltons_project`. No new mini project is invented for this campaign |
| Prompt source (existing) | Reviewed operation catalog `scripts/demo/shared-tui-tracking-demo-pack/long-horizon/suite.json` (codex cells at lines 25, 184, 342, 505, 664), timing rules from the kimi campaign's UC-04-derived ready-window rule (≥2 samples after ≥max(2.0 s, 4× capture interval) idle), behavior model reference (read-only) from `openspec/specs/codex-tui-state-tracking/spec.md` |
| Detector under test | Repo code as of campaign start. Arm A1: `FallbackCodexTuiSignalDetector` — what 0.162.1 resolves to (`shared_tui_tracking/registry.py:151-157`). Arm A2: `CodexTuiSignalDetectorV0_144_X` via `--observed-version 0.144.0` override (`registry.py:143-150`) |
| Recorder | `pixi run python -m tools.terminal_record start --mode active --tool codex --sample-interval-seconds 0.2` (5 fps, standing user directive); captures escape sequences (`capture-pane -p -e -S -`) |
| Run roots | `tmp/houmao-dev-tui-testing/<run-id>/` per `houmao-dev-tui-testing` artifact contract; campaign `evidences/` holds evidence documents, digests, and run-root references, not bulk copies |
| Driving | Tracker-blind scenario steps only (`send_text`, `send_key`, `wait_seconds`, documented `wait_for_pattern`); no `wait_for_ready`/`wait_for_active` |
| Credential hygiene | Campaign artifacts may reference or copy session rollout/event files under `CODEX_HOME`; `auth.json`, tokens, and any credential material are never copied, printed, or embedded in artifacts |

## Predeclared Arms

| Arm | Input | Analysis | Output |
| --- | --- | --- | --- |
| A1 (fallback replay — today's resolution) | Frozen `pane_snapshots.ndjson` (ANSI-stripped view) | `tools.terminal_record analyze --observed-version 0.162.1` replay vs blind labels | Per-state field mismatches for the fallback detector |
| A2 (0.144.x override replay) | Same frozen snapshots | `tools.terminal_record analyze --observed-version 0.144.0` replay vs the same blind labels | Per-state field mismatches for the newest maintained profile; decides patch-vs-rebuild |
| B (escape sequences, audit only) | Same frozen snapshots, raw escape-preserving rows | Scripted audit for OSC 133 zone markers and OSC `9;4` progress sequences per labeled state | Presence/absence table by state |
| C (structured channels, feasibility only) | Codex session event stores written under `CODEX_HOME` during the same sessions (`sessions/` rollouts, `state_*.sqlite` event tables) | Post-hoc event inventory with timestamps aligned to labeled spans | Event-coverage table for KQ-2 P2.1/P2.2; no live app-server attach this iteration |

One recording feeds Arms A1, A2, and B (the recorder already preserves escape sequences; `analyze` resolves the detector from the passed observed version). Arm C reuses the same sessions' provider-side artifacts; no extra capture is needed.

## Scenario (State Matrix)

Test cases will be specified in promptfoo-format configs under [2026-10-12-plan-1-state-matrix-capture/](2026-10-12-plan-1-state-matrix-capture/) (`session-1-lifecycle.yaml`, `session-2-operator-surfaces.yaml`, assertion contracts in `asserts/README.md`), created per the execution checklist before any launch; the YAML files are then the predeclared contract. Summary below.

Two recorded sessions, both running codex over a fresh copy of the existing Boltons fixture. Session 1 (unattended `--dangerously-bypass-approvals-and-sandbox`, delegated launch via `houmao-dev-launch-agents use launch-codex` with the campaign `CODEX_HOME` and model/effort flags): turn-lifecycle states, reusing the reviewed catalog operations. Session 2 (explicit non-bypass `as_is` launch, default approval policy, trusted workdir): operator-interaction states that unattended mode suppresses — these need new prompts because the catalog deliberately excludes confirmation states.

Session 1 operations (prompts adapted from `suite.json` codex cells, timing per the ready-window rule):

1. Cold start in the untrusted Boltons copy — capture the startup splash, any trust prompt (if rendered, select trust as a documented operator decision), the `⚠ N warning · f2 to view` indicator; open and close the F2 warnings screen.
2. Settled idle — placeholder composer `› Ask Codex to do anything`, footer; hold per the ready-window rule (≥2 samples after ≥2.0 s idle at 5 fps).
3. Editing — type a read-only prompt (`Read boltons/iterutils.py and tests/test_iterutils.py. Do not edit files. Reply with …` plus a literal suffix) without submitting, Backspace over the suffix, hold, then clear.
4. Busy phases and success — submit `Use terminal tools now. Run pwd and git status --short. Do not edit files. Reply with the working-directory …`; capture `• Working (Ns • esc to interrupt)`, the footer braille spinner, and the `Worked for …` completion marker; settle to a ready window.
5. Tool + edit workflow — read `pairwise`/`windowed`, create `tests/test_houmao_long_horizon.py`, run `python -m pytest -q tests/test_houmao_long_horizon.py`; captures sustained tool activity and multi-turn active→ready cycles.
6. Queue / pending input — submit a long prompt (the ≥35-bullet scan from the catalog), then while busy type and submit a short follow-up; capture codex's actual queued-follow-up or steer rendering (`• Messages to be submitted …` cells or equivalent); let it drain.
7. Interrupt — submit a long prompt, wait one confirmed active frame, send `Escape` once; capture `■ Conversation interrupted - use /feedback if something went wrong`; settle past the gap rule.
8. Compaction (opportunistic) — `/compact`; capture the compaction surface if it renders.
9. Exit — close the tool; capture process/pane loss.

Session 2 operations (non-bypass `as_is` launch, trusted Boltons copy, new campaign-designed prompts):

1. Command approval — submit "Run `git status --short` with your shell tool, then stop"; capture `Would you like to run the following command?` and its option list; choose the rendered deny option.
2. Edit approval — submit "Create `docs/houmao-campaign-note.md` with one sentence, then stop"; capture `Would you like to make the following edits?`; deny.
3. Permissions grant (opportunistic) — capture `Would you like to grant these permissions?` if a prompt reaches it.
4. Send-input-to-terminal (opportunistic) — capture the new `Would you like to send input to the existing terminal?` surface; requires a background terminal session, skipped with a named gap if unreachable.
5. Model picker — `/model`; capture the `Select Model and Effort` popup; cancel with Esc.
6. Trust prompt — only if Session 1's bypass launch suppressed it: relaunch without bypass in a fresh untrusted copy and capture the trust surface.

Retry countdowns, stream-disconnect/server-error cells, and context-length failures are opportunistic in both sessions (they cannot be forced reliably); absence is recorded as missing coverage, not fabricated.

Deviation noted, no spec action (user directive 2026-10-12): `openspec/specs/codex-tui-state-tracking/spec.md` encodes the 0.144-era behavior model (Worked-for marker semantics, placeholder handling, overlay families) and is used here as a read-only reference only. Campaign evidence may refute parts of it; divergences are recorded in `../evidences/` and `../reports/`, and any spec or implementation change happens only after manual review of those reports — this campaign does not modify `openspec/`.

## Gates

Pass/fail criteria declared before execution:

- G1 Recording completeness: recorder `manifest.json` has `stopped_at_utc` + `stop_reason`; `pane_snapshots.ndjson` and `input_events.ndjson` exist; `frozen-evidence.json` records SHA-256, byte size, and row counts for every bound file. FAIL → new attempt, preserve this one.
- G2 State coverage: every non-opportunistic state in the scenario has ≥1 contiguous labeled span of ≥2 samples (≥0.4 s at 5 fps). Missing states are declared as coverage gaps in the evidence doc; the iteration may still pass with named gaps.
- G3 Blind-label integrity: `labels.json` complete (every source sample labeled, all eight public fields, no overlaps) and `labels-manifest.json` frozen before any `analyze` or detector inspection. Any breach → labels discarded and re-authored from the raw recording.
- G4 Replay execution, both arms: `analyze --observed-version 0.162.1` and `analyze --observed-version 0.144.0` each complete on both sessions and emit `parser_observed.ndjson` + `state_observed.ndjson`; detector identity recorded per arm (`codex_tui`/`fallback` vs `codex_tui`/`0.144.x`).
- G5 Taint: `run_tainted` and all taint reasons recorded; a tainted run is reported as tainted, never silently treated as clean.
- G6 Unattended discipline: any unexpected confirmation prompt in Session 1 (beyond the planned trust decision in op 1) marks that span failed per the TUI-testing skill rule; the span is excluded from pass claims.

## Measurements and Decision Rules

Measurements:

1. Per-sample agreement on the two user-facing booleans first (`surface_accepting_input`, `surface_ready_posture`), grouped by labeled state, reported separately for Arm A1 and Arm A2. Then the remaining six public tracked-state fields as diagnostic detail, grouped the same way.
2. Signal survival table per KQ-1 proposition: for every hardcoded assumption in `apps/codex_tui/signals/` (prompt regex and placeholder/draft classification, status-row and activity families, `_CODEX_WORKED_PREFIX`, interruption and steer-handoff texts, overlay needles, error-cell regex inventory, provider markers) record: observed on 0.162.1 surface? detector behaved as designed? citing source sample IDs.
3. Arm B audit: count of samples containing OSC 133 / OSC `9;4` sequences, cross-tabulated by labeled state.
4. Arm C inventory: event types present in the provider event stores, timestamp alignment quality against labeled spans (feasibility input for KQ-2, not a pass/fail metric).

Decision rules (predeclared):

- A signal is **surviving** if it fires correctly on ≥95% of its state's labeled samples and on <5% of other samples.
- A signal is **broken** if it fires on <50% of its state's labeled samples, or fires on ≥5% of samples of an unrelated state.
- Otherwise **degraded**. Unreached states (coverage gap) leave their signals **unresolved**, explicitly.
- Boolean priority: false-ready and sustained false-busy errors on the two user-facing booleans outrank all per-state cosmetic mismatches; the iteration's headline metrics are the two boolean agreement rates per arm.
- Interference-only rule: codex-internal states beyond the public model (subagent rows, retry, compaction, MCP boot) are scored only on whether the public fields stay correct in their presence; failure to name the internal state is never counted as a mismatch.
- Iteration disposition: KQ-1 propositions are marked confirmed/refuted per the survival table; the A1-vs-A2 comparison decides whether the repair is a patch of the 0.144.x family or a new 0.162.x family; the mismatch catalog is the primary input to the later repair proposal.

## Execution Checklist

- [x] Freeze this plan, KQ-1 propositions, arms, gates, decision rules (this document is the predeclaration)
- [x] Create fresh run roots under `tmp/houmao-dev-tui-testing/` (one per session; never reuse a non-empty root)
- [x] Prepare one Boltons working copy per session from `tests/fixtures/test-projects/boltons` (copy, `houmao-baseline` git baseline, 437-test collection preflight per `prepare_boltons_project`); record source and copy digests
- [x] Create the promptfoo-format case specs in `2026-10-12-plan-1-state-matrix-capture/` and expand them into runner inputs: `definitions/task.md` and `definitions/scenario.json` per session, plus the TUI driver and `asserts/*.py` scripts per the kimi campaign's contracts
- [x] Delegate Session 1 launch: `houmao-dev-launch-agents use launch-codex` (unattended bypass, `CODEX_HOME=$PWD/.codex`, `-m gpt-6.1-sol -c model_reasoning_effort=medium`, untrusted Boltons workdir); verify live tmux session + pane
- [x] Start 5 fps active recording on the delegated pane before the first operation
- [x] Drive Session 1 operations 1–9 with tracker-blind steps; log operation timings
- [x] Stop recording; verify G1; freeze digests into `capture/frozen-evidence.json`
- [x] Repeat launch + record + drive + freeze for Session 2 operations 1–6 (non-bypass, trusted workdir)
- [x] Author blind ground truth from raw recordings only (G3); freeze `labels-manifest.json`
- [x] Run Arm A1 replay (`analyze --observed-version 0.162.1`) and Arm A2 replay (`analyze --observed-version 0.144.0`) on both sessions; verify G4
- [x] Run Arm B escape-sequence audit script over both snapshot streams
- [x] Run Arm C event-store inventory on the sessions' rollout files under `CODEX_HOME` (copy rollout/event artifacts only — never `auth.json` or tokens); align event timestamps to labeled spans
- [x] Score measurements against decision rules; fill the signal survival table
- [x] Write evidence docs under `../evidences/` (one per session), update KQ-1 answer, KQ-2 feasibility note, and `../debug-intent.md` status
- [x] Clean up provider-credential-adjacent temp material per the artifact contract; record cleanup status

## Results (added after completion, 2026-10-12)

All gates passed. G1: both recordings complete with digests (stop_reason carries the recorder's post-exit teardown quirk, noted in evidence). G2: every non-opportunistic state captured with ≥2-sample spans; declared gaps — tui_down (single sample), edits-form approval, permissions-grant, send-input approval, error/retry cells. G3: labels frozen 06:27:36 UTC before any replay. G4: both arms replayed both sessions (1907 + 437 samples). G5: `run_tainted=false` both sessions. G6: zero unexpected confirmation prompts.

Headline measurements (booleans, per-sample vs blind labels): A1 fallback 0.973/0.887 (s1) with 147 false-ready + 68 false-busy; A2 0.144.x 0.973/0.873 (s1) with 242 false-ready; s2 fallback 0.826/0.764. Candidate 0.162.x (monkey-patched repairs): **s1 0.9995/0.9984 (2 false-ready, 1 false-busy, all 1-sample seams), s2 1.0000/1.0000 (0/0)**. Arm B: zero OSC sequences in 2344 samples. Arm C: rollout lifecycle events align with labeled turn seams within ≤0.5 s; `turn_aborted` distinguishes operator denial.

Disposition: KQ-1 resolved (survival table in its answer); patch-vs-rebuild decided — patch the 0.144.x skeleton with the candidate repairs; the repair report names every production touch point. KQ-2 partially answered (offline oracle confirmed; live attach open).

## Corrections

- 2026-10-12 (attempt 001, run root `2026-10-12-codex-session1-lifecycle`): the recon claim "bypass goes straight to the composer, no trust screen" held only for plain `/tmp` workdirs. The Boltons working copy is a git repo, and codex 0.162.1 renders the `Trust this folder? … 1. Trust and continue / 2. Quit` screen for untrusted git-repo workdirs even under `--dangerously-bypass-approvals-and-sandbox` (and under as_is). Attempt 001 hung 90 s on the unhandled trust screen; the runner's recovery Escape hit the screen's `esc quit` and killed the TUI, then the next op crashed on the dead pane (preserved as a failed attempt, unfrozen). Session 1 op 1 and Session 2 op 1 now handle the trust screen deterministically (wait → hold → Enter → wait composer), which also moves trust-modal coverage from "unreachable" to a deterministic `startup_modal` span in both sessions; plan op lists and the Session-2 trust-relaunch fallback are superseded. Runner hardened to isolate unexpected op errors per leg instead of crashing the run.
- 2026-10-12 (session 2 launch attempt 001, `HMDEV-codex-20261012T061609`): codex 0.162.1's `--ask-for-approval` accepts only `on-request` and `never`; the legacy `untrusted` value was removed (probe exit status 2 listing possible values). Session 2's as_is posture is therefore `-a on-request -s read-only`, and the command-approval leg submits an out-of-sandbox write (`touch /tmp/houmao-codex-s2-marker.txt`) so the approval panel is forced deterministically — a plain read-only command would auto-run under the read-only sandbox. The launch failure left no run-root artifacts (launch stage precedes recording).
