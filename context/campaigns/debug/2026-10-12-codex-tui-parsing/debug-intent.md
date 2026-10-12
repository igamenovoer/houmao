# Debug Intent: Codex TUI Parsing

Date: 2026-10-12. Status: iteration 1 complete (KQ-1 resolved, KQ-2 partially answered — offline oracle confirmed, live attach open); candidate repair qualified and awaiting manual review in [reports/2026-10-12-codex-0-162-x-parsing-repair.md](reports/2026-10-12-codex-0-162-x-parsing-repair.md). Campaign directory: `context/campaigns/debug/2026-10-12-codex-tui-parsing/`.

## Problem Statement

Houmao tracks CLI agent state by scraping terminal surfaces. Its codex detector (`src/houmao/shared_tui_tracking/apps/codex_tui/`) ships two maintained profiles — `CodexTuiSignalDetectorV0_116_X` (registry interval [0.116.0, 0.117.0)) and `CodexTuiSignalDetectorV0_144_X` ([0.144.0, 0.145.0), built from recorded surfaces) — plus a silent `FallbackCodexTuiSignalDetector` that catches every other version (`src/houmao/shared_tui_tracking/registry.py:135-157`). The currently installed codex is `codex-cli 0.162.1` (verified `codex --version` on this host, 2026-10-12; source reference `extern/orphan/codex` @ 322bbf4, 2026-10-10). At campaign planning, 0.162.1 matches neither maintained interval and silently resolves to the fallback detector — the same registry disease kimi-code had, repaired there by `openspec/changes/archive/2026-10-12-raise-kimi-code-floor-2-1-1/` (floor + qualified detector, no fallback). Launch side is also misaligned: launch policy `src/houmao/agents/launch_policy/registry/codex.yaml` declares strategy `codex-unattended-0.116.x` with `supported_versions: ">=0.140.0"` (live-probed on 0.140.0), so launches claim support for 0.162.1 while tracking silently degrades. The campaign question: what is the appropriate way to determine codex 0.162.x turn state (idle, editing, busy, approval pending, queued input, interrupted, exited) — repaired text scraping, escape-sequence channels, or structured non-TUI interfaces?

## User-Facing Requirement (carried over from the kimi campaign, directive 2026-10-10)

The downstream user does not need a fine-grained state taxonomy. The product contract is two coarse booleans about the TUI surface:

1. **Ready to enter prompt**: the operator can type into the TUI right now (the composer accepts keystrokes). Maps to `surface_accepting_input` (editing facet: `surface_editing_input`).
2. **Accept prompt**: a prompt submitted now starts processing immediately instead of sitting in the provider-owned queue because the agent is busy. Maps to `surface_ready_posture`, adjudicated operationally.

Fine-grained states remain diagnostic observables only; success and repair priority are judged on the two booleans.

## Detection Target Boundary (carried over)

The detection target is houmao's existing public state model, `TrackedStateSnapshot` / `TrackedTimelineState` (`src/houmao/shared_tui_tracking/models.py`). Codex-internal states (subagent activity, compaction, retry countdowns, MCP server boot, background-terminal waits) enter the evaluation only as interference: they must leave the public fields correct and never manufacture a false `ready` or false `idle`. The campaign proposes no new public fields.

## Starting Evidence

Informal observations from a source audit and a live recon on 2026-10-12 (this host; codex 0.162.1 in tmux, `CODEX_HOME=$PWD/.codex`, ChatGPT login verified via `codex login status`; model `gpt-6.1-sol`, effort `medium`; trusted workdir; unattended bypass launch). Iteration 1 must re-capture these as formal, reproducible evidence.

Version/registry gap (verified by inspection):

1. `registry.py:135-157`: codex intervals [0.116.0, 0.117.0) and [0.144.0, 0.145.0); 0.162.1 → `FallbackCodexTuiSignalDetector` (`detector_version="fallback"`, conservative prompt classification, temporal inference off). No floor, no error, no operator-visible warning.
2. `codex.yaml` launch policy claims `>=0.140.0`; tracking has no maintained profile above 0.144.x. Strategy id still says `0.116.x`.

Broken or stale assumptions (source- or live-confirmed):

3. Interrupt text drift: detector expects `Conversation interrupted - tell the model what to do differently. ` (`signals/interrupted.py:12`); 0.162-era source renders `■ Conversation interrupted - use /feedback if something went wrong` (`extern/orphan/codex/codex-rs/tui/src/chatwidget/input_restore.rs:332`; live-confirmed after Esc). Suffix changed and a `■` marker prefix added.
4. Completion-marker drift: detector prefix `─ Worked for ` (`profile.py:53`); live 0.162.1 renders `  Worked for 3s • 3:30 AM` — no `─` prefix. Completion-marker detection is broken.
5. Composer is unboxed: idle composer is `› Ask Codex to do anything` with no `╭─…╮` border box, and the transcript echoes submitted user prompts with the same `›` token the prompt regex (`_CODEX_PROMPT_RE = ^\s*›(.*)$`, `signals/prompt_behavior.py:13`) keys on. Prompt-area extraction must disambiguate composer from transcript echoes.
6. Footer redesigned: `GPT-6.1-Sol medium · <cwd> · <last-task-summary>` plus `? for shortcuts` and `⚠ N warning · f2 to view`; busy adds a braille spinner suffix (`· ⠹`). Any footer-keyed assumption needs re-verification.
7. New approval surface not covered by the detector's overlay needles: `Would you like to send input to the existing terminal?` (`tui/src/bottom_pane/approval_overlay.rs:258-260`) alongside the known `Would you like to run the following command?` / `…make the following edits?` / `…grant these permissions?` (all still present in source).
8. Startup splash: a large ASCII-art logo renders on cold start (live capture); any provider-marker or launch-detection assumption must tolerate it.

Unchanged in source (rendering equivalence unverified — iteration 1 measures): `Working (Ns • esc to interrupt)` status row format (`status_indicator_widget.rs:452`; live capture shows `• Working (2s • esc to interrupt)` matching `^\s*• (.+?) \((.+esc to interrupt.*)\)`), `Select Model and Effort` popup, `Reconnecting`, `• Waited for background terminal · `, `Press enter to confirm or esc to cancel`, trust-directory onboarding (`tui/src/onboarding/trust_directory.rs`).

Fixture poverty: `tests/fixtures/shared_tui_tracking/codex/` holds only two `stale_active_*` ANSI captures; `tests/unit/shared_tui_tracking/test_codex_prompt_behavior.py` and `test_codex_tui_session.py` encode 0.116.x/0.144.x-era surfaces. No 0.162.x fixture exists.

Structured channels worth oracle-testing (codex-specific, unlike kimi): codex app-server JSON-RPC (houmao already ships a `codex_app_server` launch backend) and `codex exec --json` event streams.

## Comparison Arms

| Arm | Approach | What is evaluated |
| --- | --- | --- |
| A1 | Fallback detector replay (what 0.162.1 resolves to today) | Baseline mismatch catalog vs blind ground truth |
| A2 | `CodexTuiSignalDetectorV0_144_X` via registry override | Does the newest maintained profile already cover 0.162.x? |
| B | Escape-sequence audit (OSC 133 / OSC 9;4 and friends) on escape-preserving captures | Presence/absence by state; codex TUI is ratatui-based, survival unknown |
| C | Structured event channels (app-server JSON-RPC, `exec --json`) | Oracle for validating Arms A; candidate replacement where a TUI is present |

One recording feeds Arms A1, A2, and B; Arm C needs a parallel event capture during the same sessions.

## Scope and Implementation Boundary

In scope: codex-cli 0.162.1 interactive TUI behavior as rendered in tmux on this host; the houmao codex_tui detector profiles, registry version selection, and terminal_record analyze path as analysis subjects; recording/replay tooling and fixture capture into this campaign's `evidences/`.

Methodology — record first, test second (identical to the kimi campaign): every live probe is recorded with the repo's terminal recorder (`pixi run python -m tools.terminal_record start --mode active --tool codex --sample-interval-seconds 0.2`, 5 fps per the standing user directive; captures escape sequences). Analysis and labeling run offline against frozen recordings. Ad-hoc tmux `capture-pane` probes are reconnaissance only, not evidence.

Binding rules adopted from `skillset/dev/houmao-dev-tui-testing` and `skillset/dev/terminal-recorder-workflow` (same as the kimi campaign):

1. Launches are delegated to `skillset/dev/houmao-dev-launch-agents` (`launch-codex`, unattended `--dangerously-bypass-approvals-and-sandbox` by default; explicit non-bypass launch for operator-surface sessions). Credential lane (user directive 2026-10-12): `CODEX_HOME=$PWD/.codex` (project-local codex home with ChatGPT login; verified `codex login status` 2026-10-12). Default test model (user directive 2026-10-12): `gpt-6.1-sol` with medium reasoning effort (`-m gpt-6.1-sol -c model_reasoning_effort=medium`) unless a scenario specifies otherwise. A confirmation prompt during an unattended run is a failed or incomplete test, recorded as such.
2. Recording starts before the first operation and stops explicitly; the run is frozen with SHA-256 digests before any labeling or replay. Failed or tainted attempts are preserved, never deleted.
3. Artifact authority: `pane_snapshots.ndjson` is the machine replay source of truth; `labels.json` is independent ground truth; tracker/analyze output is implementation output, never ground truth.
4. Blind-label boundary: ground truth authored from raw recordings alone, using the eight public tracked-state fields from `skillset/dev/houmao-dev-tui-testing/references/state-labeling.md` (including the modal convention added by the kimi campaign), with complete non-overlapping sample coverage.
5. Tracker-blind driving: scenario steps use `send_text`, `send_key`, `wait_seconds`, and direct documented `wait_for_pattern` only.
6. Cadence: 5 fps per standing user directive; if a key question needs cadence-sensitivity above 5 Hz, record that iteration's source at 20 Hz and derive down, naming the deviation.

`extern/orphan/codex` (read-only source reference) remains read-only. Production code under `src/houmao/` remains read-only for the duration of the campaign. Experiment tooling lives in `scripts/explore/codex-tui-parsing/` (monkey-patching production seams at runtime, kimi precedent); candidate repairs are exercised there only. Integration into `src/houmao/` happens only after manual review of the campaign's reports (user directive 2026-10-12); this campaign produces no OpenSpec artifacts and modifies nothing under `openspec/`.

Out of scope: claude_code and kimi_code detector profiles; codex headless (`codex exec`) as a launch-mode change; CAO provider work; changes to codex configuration beyond probe setup; implementation of any fix in `src/houmao/`.

## Success Criteria

Resolution means the following are answered with evidence under `evidences/` and synthesis in `reports/`:

1. A validated signal set (per arm) that decides both user-facing booleans on codex 0.162.1 across the driven state matrix, with fine-grained states as diagnostic coverage for where each boolean flips.
2. Each signal's reliability classified (stable / version-fragile / unreliable), with the exact 0.162.1 capture proving it.
3. A recommendation naming the appropriate parsing approach per state, ready to become an implementation proposal and a fixture corpus for `tests/fixtures/shared_tui_tracking/codex/`.
4. A disposition on codex registry posture: whether to mirror kimi (floor at the qualified version, no fallback) and how launch policy `supported_versions` realigns.

## No-Product-Change Declaration

This campaign is an isolated diagnostic. It does not authorize changing production code under `src/houmao/`, test fixtures under `tests/`, anything under `openspec/`, the codex source checkout, or codex's own configuration files beyond temporary probe needs. Findings feed a later integration, gated on manual review of `reports/` (user directive 2026-10-12).

## Key Questions and Iterations

- [KQ-1: Which text-scraping signals survive on codex 0.162.1?](key-questions/KQ-1-signal-survival.md) — resolved 2026-10-12 (survival table + per-proposition verdicts in the answer).
- [KQ-2: Can codex structured event channels serve as the state oracle?](key-questions/KQ-2-structured-channels.md) — partially answered 2026-10-12 (rollout stream is a viable offline oracle; live app-server attach unverified).
- [Iteration 1: codex 0.162.1 state-matrix capture and detector gap analysis](iterations/2026-10-12-plan-1-state-matrix-capture.md) — complete 2026-10-12; all gates passed with declared coverage gaps.
- Synthesis: [codex 0.162.x parsing repair report](reports/2026-10-12-codex-0-162-x-parsing-repair.md) — fix list + qualification scores, awaiting manual review before any integration.
