# Debug Intent: Kimi Code TUI Parsing

Date: 2026-10-10. Updated: 2026-10-10. Status: iteration 1 planned. Campaign directory: `context/campaigns/debug/2026-10-10-kimi-code-tui-parsing/`.

## Problem Statement

Houmao tracks CLI agent state by scraping terminal surfaces. Its kimi-code detector (`src/houmao/shared_tui_tracking/apps/kimi_code/profile.py`) and the server-side surface mapping (`src/houmao/server/tui/parser.py`) were built against recorded kimi-code 0.11.x and 0.23.x surfaces. The currently installed and released kimi-code is 2.1.1 (verified `kimi --version` on this host; source reference at `extern/orphan/kimi-code` @ 419aced). Registry posture correction (2026-10-10, post-merge 8ad0854b): at campaign planning the registry had only [0.11.0,0.12.0) and [0.23.0,0.24.0) intervals, so 2.1.1 silently fell back to `FallbackKimiCodeSignalDetector`; the same-day merge of `main` into `devel` replaced both profiles with a single `KimiCodeSignalDetectorV0_34_PLUS` (registry.py:120-127, minimum (0,34,0), unbounded maximum, `activity_window_lines=4`, temporal growth disabled, profile note `qualification-pending`). Kimi 2.1.1 now resolves to that profile (verified by registry resolve on this host), so it is the detector under test. Its hardcoded surface assumptions live in the shared `_BaseKimiCodeSignalDetector` and remain 0.11-era; several no longer match what 2.1.1 renders. The campaign question: what is the appropriate way to determine kimi-code 2.1.x turn state (idle, editing, busy sub-phases, approval pending, question pending, queued input, interrupted, exited) — repaired text scraping, terminal escape-sequence channels, or structured non-TUI interfaces?

## User-Facing Requirement (directive 2026-10-10)

The downstream user does not need the fine-grained state taxonomy for its own sake. The product contract is two coarse booleans about the TUI surface:

1. **Ready to enter prompt**: the operator can type into the TUI right now (the composer accepts keystrokes). Maps to the public ground-truth field `surface_accepting_input` (editing facet: `surface_editing_input`).
2. **Accept prompt**: a prompt submitted now starts processing immediately instead of sitting in the provider-owned queue because the agent is busy. Maps to `surface_ready_posture`, adjudicated operationally: a submitted prompt must begin immediately for this to be `yes`.

Fine-grained states (busy sub-phases, approval and question dialogs, queued input, interrupts, exit) remain in the campaign as diagnostic observables: they are the situations that flip the two booleans, and the mismatch catalog needs them to explain false-ready and false-busy failures. Success and repair priority are judged on the two coarse booleans; per-state detail is supporting evidence, not the deliverable.

## Detection Target Boundary (directive 2026-10-10)

The detection target is bounded by houmao's existing public state model, `TrackedStateSnapshot` / `TrackedTimelineState` (`src/houmao/shared_tui_tracking/models.py:70-95, 263-285`): the eight public fields, with `turn_phase` already coarse (`ready | active | unknown`). That model is what downstream consumers read, and it is the whole contract. A TUI agent may internally expose far richer state (agent-swarm orchestration rows, compaction progress, retry counters, sub-phase spinners); this campaign has no interest in identifying those states as states. They enter the evaluation only as interference: a swarm row, a retry banner, or a compaction indicator must still leave the public fields correct (turn stays `active`, ready posture stays `no`), and must never manufacture a false `ready` or a false `idle`. The campaign proposes no new public fields and no expansion of the tracked-state vocabulary.

## Starting Evidence

Initial observations from a source analysis and a live probe conducted on 2026-10-10 (this host, kimi 2.1.1 in tmux, project OAuth credentials). These are informal observations; iteration 1 must re-capture them as formal, reproducible evidence.

Broken or stale assumptions (source + live confirmed):

1. Activity label regex `/\b(working|thinking)\.\.\./` (profile.py:30) matches nothing in 2.1.1. Live capture shows `⠦ Thinking… · Tip: …` and `⠼ Working… · Tip: …` (capitalized, Unicode ellipsis U+2026; kimi-code `apps/kimi-code/src/tui/kimi-tui.ts:3503,3517`). Because braille frames without a matching label are discarded (profile.py:516 post-merge), braille-phase activity is invisible, so busy state flickers and `success_candidate` can false-fire mid-turn.
2. Tool-approval option labels changed to `1. Approve once`, `2. Approve for this session`, `3. Reject`, `4. Reject with feedback` (live capture; kimi-code `reverse-rpc/approval/adapter.ts:7-12`). The existing choice regex still matches by prefix, but committed fixtures depict the old labels. Plan review keeps `Approve`/`Reject`/`Revise`; both vocabularies exist.
3. Editor placeholder text no longer exists; the empty 2.1 editor is `> ` plus an inverse-space cursor (`\x1b[7m \x1b[0m`, `packages/pi-tui/src/components/editor.ts:678`). The `\x1b[2m` dim-placeholder classification (profile.py:453 post-merge) is dead.
4. Footer changed: line 1 is `<model> thinking[: <effort>]  <cwd>  <rotating tips>`, line 2 is `context: N% (used/total)` (live: `K3-256k thinking: high  /tmp/kimi-probe`, `context: 9% (21.9k/256k)`). `shift+tab:` is gone; `/model:` survives only as a rotating tip; the footer is user-customizable via `[status_line]` in tui.toml (changelog #2255), so footer scraping is unreliable by design.
5. New startup modal `Trust this folder?` (live capture) is not covered by the startup-modal needles in `src/houmao/server/tui/parser.py:226-241`.
6. New uncovered interactive surfaces: AskUserQuestion dialog (` question` title, `[N]` options, `components/dialogs/question-dialog.ts`) and goal-start permission prompt (`Approve CreateGoal?`, `components/dialogs/goal-start-permission-prompt.ts`). An agent blocked on either currently reads as idle/unknown.
7. New busy-phase indicators with no detector coverage: `Retrying (N/M) · <ErrorName> · in Xs` (`tui/utils/step-retry.ts`), `● Compacting context…` (`components/dialogs/compaction.ts`), subagent/swarm progress rows (`Orchestrating…`, braille + `Running`).
8. `server/tui/parser.py` hardcodes the parser preset version regardless of the resolved detector version; pre-merge value `"0.23.x"` (parser.py:140-142), post-merge value `">=0.34.0"` (parser.py:142).

Unchanged and still valid (live confirmed): editor box `╭─…╮` / `│ >` / `╰─…╯`; moon-spinner busy frames without label; all five approval headers (`Run this command?`, `Write this file?`, `Apply these edits?`, `Stop this task?`, `Ready to build with this plan?`) bounded by `─` rules and replacing the editor; queue hints (`↑ to edit · ctrl-s to steer immediately` and two siblings, `components/panes/queue-pane.ts:31-34`); interrupt strings (`Interrupted by user`, capitalized — detector lowercases before matching; `Error: step interrupted (<reason>)`).

New machine-readable channels present in 2.1.1 that may be more appropriate than text scraping: OSC 133 zone markers on transcript lines (`constant/rendering.ts:9-11`), OSC `9;4;3` indeterminate progress while busy / `9;4;0` when idle (`packages/pi-tui/src/terminal.ts:9-10`, `kimi-tui.ts:3847-3855`), `kimi -p --output-format stream-json` NDJSON events, lifecycle `[[hooks]]` (TurnStarted, UserPromptQueued, TaskStarted, SessionHeartbeat, approval lifecycle), ACP/server event streams.

CAO contrast: the pinned CAO checkout (`extern/tracked/cli-agent-orchestrator` @ 0fb3e51) added a `kimi_cli` provider on 2026-03-13 that targets the archived legacy Python kimi-cli (prompt emoji `💫/✨`, `Welcome to Kimi Code CLI!` banner, `kimi --yolo`, `~/.kimi/config.toml`), not kimi-code 2.x. It cannot serve as a reference implementation for this campaign.

## Comparison Arms

| Arm | Approach | What is evaluated |
| --- | --- | --- |
| A | Repaired text scraping (2.1.x detector profile on plain capture-pane text) | Can updated regexes/strings recover all required states with acceptable reliability? |
| B | Escape-sequence signals (OSC 133 zones, OSC 9;4 progress) via `capture-pane -e` | Do the sequences survive tmux capture, and do they distinguish busy/idle/approval more reliably than text? |
| C | Structured event channels (hooks, print-mode stream-json, ACP/server) | Can they act as the state oracle for validating Arms A/B, and are they a viable replacement where a TUI is present? |

Arm A is the compatibility path (fits the existing detector/registry architecture); Arms B and C are candidate superior paths. The campaign compares detection reliability per state across arms, not just whether Arm A can be patched.

## Scope and Implementation Boundary

In scope: kimi-code 2.1.1 interactive TUI behavior as rendered in tmux on this host; the houmao kimi_code detector profile, registry version selection, and server/tui parser mapping as analysis subjects; recording and replay tooling and fixture capture into this campaign's `evidences/`.

Methodology — record first, test second: for ease of debugging, every live probe is recorded with the repo's terminal recorder (`pixi run python -m tools.terminal_record start --tool kimi`, implementation `src/houmao/terminal_record/service.py`) at a 5 fps sampling interval (`--sample-interval-seconds 0.2`, per user directive 2026-10-10). Analysis, detector experiments, and labeling then run offline against the frozen recording (`analyze`, `derive-stream`, `validate`) rather than against the live session, so every claim is reproducible from a stored artifact and raw snapshots land in `evidences/`. Ad-hoc tmux `capture-pane` probes (plain and `-e`) are allowed for reconnaissance only; their output does not count as campaign evidence unless re-captured through a recorded run.

The campaign follows the maintained TUI-testing workflow defined by the repo skills `skillset/dev/houmao-dev-tui-testing` (record → label → replay → compare → render-video) and `skillset/dev/terminal-recorder-workflow` (recorder operation and artifact authority). Binding rules adopted from those skills:

1. Launches are delegated to `skillset/dev/houmao-dev-launch-agents` (`launch-kimi-code`, unattended mode); the campaign never reconstructs provider launch commands or credentials itself. A confirmation prompt during an unattended run is a failed or incomplete test, recorded as such, not clicked through silently.
2. Recording starts before the first operation and stops explicitly via `tools.terminal_record stop`; the run is frozen with SHA-256 digests (recorder manifest, `pane_snapshots.ndjson`, `input_events.ndjson`, runtime observations, scenario, operation log) before any labeling or replay. Failed or tainted attempts are preserved, never deleted; retries get a new run root or numbered attempt.
3. Artifact authority: `pane_snapshots.ndjson` is the machine replay source of truth; `session.cast` is human review only; `labels.json` is independent ground truth; `state_observed*.ndjson` and any tracker output are implementation output, never ground truth.
4. Blind-label boundary: ground truth is authored from raw recordings alone, without inspecting detector, parser, or tracker output. Ground truth uses the eight public tracked-state fields from `skillset/dev/houmao-dev-tui-testing/references/state-labeling.md` (diagnostics_availability, surface_accepting_input, surface_editing_input, surface_ready_posture, surface_pending_input, turn_phase, last_turn_result, last_turn_source), with complete non-overlapping sample coverage.
5. Tracker-blind driving: scenario steps use `send_text`, `send_key`, `wait_seconds`, and direct documented `wait_for_pattern` only; never `wait_for_ready` / `wait_for_active` or other detector-owned gates.
6. Cadence note: the skills' canonical capture rate is 20 Hz so that `derive-stream` can produce deterministic lower-cadence variants (10/5/2 Hz, seeded jitter/drop/burst). This campaign records at 5 fps per user directive, which caps derived streams at ≤5 Hz; if a key question requires cadence-sensitivity analysis above 5 Hz, record that iteration's source at 20 Hz and derive down, naming the deviation in the iteration plan.

Use recorded live sessions of the installed kimi 2.1.1 (project OAuth credentials already configured) and the local source checkout for ground truth. `extern/orphan/kimi-code` (read-only source reference) and `extern/tracked/cli-agent-orchestrator` (submodule) remain read-only. Production code under `src/houmao/` remains read-only for the duration of the campaign; writing updated detectors, fixtures, or parser changes is follow-up work after the campaign resolves.

Out of scope: claude_code and codex_tui detector profiles; CAO provider rewrites; kimi-code fullscreen (`tui_mode = "fullscreen"`) mode unless a key question is opened for it; changes to kimi-code configuration beyond what probe setup requires; implementation of any fix in `src/houmao/`.

## Success Criteria

Resolution means the following are answered with evidence captured under `evidences/` and synthesized in `reports/`:

1. A validated signal set (per arm) that decides both user-facing booleans on kimi-code 2.1.1 across the driven state matrix: ready-to-enter-prompt and accept-prompt. Fine-grained state discrimination (idle vs editing, busy sub-phases, approval vs question dialogs, queued input, interrupted, exited) is required as diagnostic coverage for locating where each boolean flips, not as an end in itself.
2. Each signal's reliability classified (stable / version-fragile / unreliable), with the exact 2.1.1 capture proving it.
3. A recommendation naming the appropriate parsing approach per state (text, escape sequence, or event channel), ready to become an implementation proposal and a fixture corpus for `tests/fixtures/shared_tui_tracking/kimi_code/`.
4. A disposition on whether the version-registry/fallback behavior for unknown future kimi versions should change (fail loudly vs fall back silently).

## No-Product-Change Declaration

This campaign is an isolated diagnostic. It does not authorize changing production code under `src/houmao/`, test fixtures under `tests/`, the kimi-code source checkout, the CAO submodule, or kimi-code's own configuration files beyond temporary probe needs. Findings feed a later implementation change, proposed and reviewed separately.

## Key Questions and Iterations

- [KQ-1: Which text-scraping signals survive on kimi-code 2.1.1?](key-questions/KQ-1-signal-survival.md) — planned; propositions KQ-1.1–1.5 cover prompt detection, activity labels, approval/question dialogs, queue/interrupt strings, and footer markers.
- [Iteration 1: kimi-code 2.1.1 state-matrix capture and detector gap analysis](iterations/2026-10-10-plan-1-state-matrix-capture.md) — planned; two recorded 5 fps sessions (turn-lifecycle states under `--auto`, operator-interaction states in manual mode), Arms A (detector replay vs blind ground truth) and B (escape-sequence audit) over one frozen recording.

Remaining candidate key questions, not yet opened: KQ-2 — do OSC 133 / OSC 9;4 sequences survive tmux capture and track busy/idle reliably (Arm B feasibility, seeded by iteration 1's audit); KQ-3 — can hooks or print-mode stream-json serve as the ground-truth oracle for labeling captures (Arm C feasibility).
