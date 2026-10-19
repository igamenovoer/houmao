# Iteration Plan 1: Hook Capture Matrix

Status: executed (iteration 1 complete, 2026-10-19; G0-G3 passed, see Result). Date: 2026-10-19. Campaign: [debug-intent.md](../debug-intent.md).

Questions owned: [KQ-1](../key-questions/KQ-1-settings-injection.md), [KQ-2](../key-questions/KQ-2-delivery-semantics.md), [KQ-3](../key-questions/KQ-3-payload-catalog.md), [KQ-4](../key-questions/KQ-4-background-work.md). KQ-5 replays these captures in a later iteration.

## Question / Answer Sought

Can a launch-owned observer configuration capture a complete, correctly ordered hook stream for real Claude TUI sessions, and what do the event payloads actually contain? Deliverable: at least 5 (target 7) paired captures (hook stream + pane recording + labels) covering the campaign matrix, plus a payload catalog.

## Frozen Workload

- Host claude: 2.1.303 via `~/.local/bin/claude-deepseek` (DeepSeek anthropic endpoint, launcher-pinned model `deepseek-flash[1m]`); no `--model` argument is passed, and the in-session bootstrap check verifies the model shows DeepSeek Flash (stop and consult if it shows anything else).
- Floor check: 2.1.296 side-by-side install (scratch bun install, no replacement of the host install) for a single S1-repeat capture; skipped with a named gap if not installable.
- Workloads: throwaway git-less directories under `tmp/hook-capture/<scenario>/`; pane recording at 5 fps via the repo's terminal-record tooling; hook capture via the iteration-1 harness in `scripts/explore/claude-hook-observation/`.
- Frozen prompts per session (exact text in the arms table below); no improvisation mid-run.
- Cost discipline per the intent's credential and cost lane: launcher-pinned `deepseek-flash[1m]` only, short prompts, no sessions beyond this plan.

## Predeclared Arms

| Session | Launch | Frozen prompt / actions | Predeclared expectation |
| --- | --- | --- | --- |
| S0 (gate) | observer settings, skip-permissions | "Reply with exactly: OK" | `SessionStart` + `UserPromptSubmit` + `Stop` arrive; provider behavior unchanged |
| S1 normal | as S0 | "Reply with exactly: OK", then "What is 2+2? Reply with just the number." | full turn cycle x2; `SessionEnd` on exit if supported |
| S2 direct input | as S0 | typed via tmux send-keys: "Reply with exactly: OK" | `UserPromptSubmit` fires without any gateway submission record |
| S3 permission | deepseek launcher env replicated WITHOUT `--dangerously-skip-permissions` (same endpoint, runtime key read, same model pins) | "Create a file named /tmp/houmao-hook-allow.txt containing hello" (allow at modal), then "Create a file named /tmp/houmao-hook-deny.txt containing hello" (deny at modal) | `PermissionRequest` before modal paint; resolution event on allow; silence on deny per design Gap 4 |
| S4 compaction | as S0 | "Read README.md and summarize in one sentence.", then `/compact` via send-keys, then "Reply with exactly: OK" | `PreCompact`/`PostCompact` payloads; turn identity continuity across compaction |
| S5 background | as S0 | "Run `sleep 90` in the background with run_in_background, then reply with exactly: DONE" | `Stop` with `background_tasks`; whatever fires at sleep completion (~90 s bounded idle wait, no token cost); any task/notification events recorded |
| S6 interrupt | as S0 | "Write a long essay about recursion." then Esc mid-generation | whether Esc emits `Stop`; best-effort `StopFailure` arm via any available fault lane (declared before the run) |
| S7 queue + resume | as S0 | "Write a long essay about queues." then type "Reply with exactly: OK" while busy; exit; relaunch with `--resume` | event ordering at queue consumption; new `SessionStart` with resume source |

## Harness Build (pre-capture, part of this iteration)

- [x] `scripts/explore/claude-hook-observation/observer_settings.py`: generates the session-scoped observer settings JSON (v1 event set, HTTP handlers plus command handler for `SessionStart`, token via env reference)
- [x] `scripts/explore/claude-hook-observation/collector.py`: stdlib loopback collector (bearer token, sequence stamping, append-only `events.ndjson`, ack-before-disk)
- [x] `scripts/explore/claude-hook-observation/emit_hook.py`: command-hook fallback emitter (exit 0, stdout silent, file fallback)
- [x] `scripts/explore/claude-hook-observation/run_capture.py`: one-command scenario runner (launch tmux + claude with observer settings, drive frozen prompt/actions, record pane at 5 fps, write labels template)
- [x] `scripts/explore/claude-hook-observation/README.md`: harness usage and layout

## Gates (checked in order; a failed gate stops the iteration)

- [x] G0 harness: collector and emitter pass a local self-test with a synthetic POST (no provider involved)
- [x] G1 S0 smoke: `SessionStart` arrives within 15 s of provider start; provider behaves normally; in-session model shows DeepSeek Flash (launcher-pinned)
- [x] G2 injection honored: the observer settings produce events for every v1 event the scenario exercises; a silent event family is recorded, not ignored
- [x] G3 pairing: every capture has pane recording + hook stream + labels with matching time base (monotonic offset recorded)

## Measurements and Decision Rules

- Per-event delivery latency (event timestamp vs visible surface frame), per-session event sequence dump, payload field inventory per event type.
- KQ-1 resolved when G0-G3 pass and P1.1-P1.4 each have a recorded yes/no with evidence.
- KQ-2 timing propositions answered from S3/S6/S7 sequences; P2.3 measured by matched-prompt wall-time comparison (hooks on S1 vs a hooks-off repeat of S1's prompts, same model).
- KQ-3 catalog built from all captures; absent fields named per event.
- KQ-4 answered from S5; if no completion evidence exists, the payload-mirror fallback is confirmed as the v1 limit and the revisit trigger is written.

## Execution Checklist

- [x] Build harness (items above)
- [x] G0 self-test
- [x] S0 gate session
- [x] S1-S7 captures in order, each with labels written same-day
- [x] Hooks-off matched-prompt control for P2.3
- [x] Floor check at 2.1.296 (S1 repeat) or named gap
- [x] Payload catalog written to `evidences/2026-10-19-hook-payload-catalog.md`
- [x] KQ-1..KQ-4 answer sections updated with evidence links

## Result

Iteration 1 executed successfully on 2026-10-19. All gates G0-G3 passed (G0: self-test 4/4; G1: SessionStart < 1 s in every session; G2: every exercised family produced events with silent families named per session; G3: pane recording + hook stream + labels + monotonic/UTC pair in all ten runs). Ten paired captures (49 hook events total), exceeding the 7-session target.

### Captured Sessions

| Session | Run root (`tmp/hook-capture/…`) | Events | Evidence |
| --- | --- | --- | --- |
| S0 gate | `s0/run-20261019T131518Z` | 3 | [evidence](../evidences/2026-10-19-s0-gate-smoke.md) |
| S1 normal | `s1/run-20261019T131758Z` | 5 | [evidence](../evidences/2026-10-19-s1-normal-multiturn.md) |
| S1 hooks-off control | `s1-control/run-20261019T140530Z` | 0 (by design) | [evidence](../evidences/2026-10-19-s1-hooks-off-control.md) |
| S2 direct input | `s2/run-20261019T131948Z` | 3 | [evidence](../evidences/2026-10-19-s2-direct-input.md) |
| S3 permission | `s3/run-20261019T132946Z` | 9 | [evidence](../evidences/2026-10-19-s3-permission-lane.md) |
| S4 compaction | `s4/run-20261019T133729Z` | 9 | [evidence](../evidences/2026-10-19-s4-compaction.md) |
| S5 background | `s5/run-20261019T134126Z` | 6 | [evidence](../evidences/2026-10-19-s5-background-work.md) |
| S6 Esc interrupt | `s6/run-20261019T134703Z` | 3 | [evidence](../evidences/2026-10-19-s6-esc-interrupt.md) |
| S7 queue + resume | `s7/run-20261019T135815Z` | 6 | [evidence](../evidences/2026-10-19-s7-queue-resume.md) |
| Floor S1 repeat (2.1.296) | `s1/run-20261019T141215Z` | 5 | [evidence](../evidences/2026-10-19-floor-2-1-296-s1-repeat.md) |

Supporting (flawed or superseded) runs retained: `s0/run-20261019T131232Z` (first gate attempt, model-needle abort), `s3/run-20261019T132241Z` and `s3/run-20261019T132754Z` (auto-mode and deny-key attempts), `s4/run-20261019T133547Z` (Stop-occurrence flaw), `s7/run-20261019T135152Z` and `s7/run-20261019T135559Z` (resume gate flaws), `s1-control/run-20261019T140227Z` (settle-heuristic flaw).

### Headline Findings per KQ

- KQ-1: `--settings` honored at 2.1.303 and 2.1.296; HTTP hooks and the SessionStart command-hook path both deliver; P1.4 untested.
- KQ-2: queued input fires `UserPromptSubmit` at type time (ordering `UPS, UPS, Stop, Stop`); PermissionRequest precedes modal paint (lead > 0, < 2 s at 1 s stamp granularity); hook cost unmeasurable against the control floor; Esc emits nothing; StopFailure unreachable.
- KQ-3: catalog confirmed with deviations (undocumented `effort`/`permission_mode` everywhere, resume cost fields, ghost `<task-notification>` prompt shape, `background_tasks` element shape; `UserPromptSubmit.source` never sent); floor payloads identical.
- KQ-4: background completion fires a provider-initiated ghost turn (`<task-notification>` UserPromptSubmit + Stop); `Stop.background_tasks` is the live work mirror; TUI indicator corroborates. Payload-mirror fallback not needed as the v1 limit.

### Deviations from the Frozen Workload (all recorded in their evidence docs)

1. S3 lane pins `--permission-mode manual`: without it 2.1.303 boots the no-bypass lane into auto mode, which auto-allows tools with no modal and no PermissionRequest. Prompt texts unchanged.
2. S3 modal keys verified from rendering: allow `1`, deny `3` (option layout varies by tool). S6 exit-path flaw (`/exit` appended to the restored draft) fixed; arm evidence unaffected.
3. S7 resumes by explicit session id (picker is cross-project on 2.1.303; picker surface preserved in attempt artifacts).
4. Model gate needle reinterpreted: the TUI banner renders the raw pinned id `deepseek-flash[1m]`, not the friendly name the plan text assumed.

### Named Leftovers

- P1.4 (conflicting `--settings`) unresolved: missing arm, one launch with a pre-existing settings source.
- P2.5 (StopFailure) unreachable: missing control, a session-scoped API-fault injector.
- P4.4 (Notification idle_prompt) unexercised: Notification not in the v1 subscribed set.
- SessionEnd deliberately unsubscribed (v1 = 9 events); its absence is recorded, not assumed.
- `launch.json` does not record the resolved provider binary SHA-256 (named in the S0 evidence).
- Collector `received_at_utc` stamps at 1 s granularity; sub-second P2.2 lead measurement needs ms stamping (iteration-2 improvement).

### Addendum (2026-10-19, same-day): home-injection coexistence arm

One additional live arm ran after the main matrix: S1 repeated with the observer block marker-merged into a scratch managed home's `settings.json` (`CLAUDE_CONFIG_DIR`, no `--settings` passed at all) alongside a dummy operator hook. All five checks passed: SessionStart < 1 s from the home layer, full event delivery with byte-identical payload inventory versus the `--settings` run, token interpolation clean, the operator hook fired twice undisturbed, and the flag slot is provably free. Two findings: the workspace-trust dialog appears on a fresh scratch home (onboarding keys alone do not suppress it; the project-trust keys seeded by the `claude.ensure_project_trust` provider hook are load-bearing), and managed launch plans have no operator args passthrough while the raw launch-helper CLI does without owning `--settings` (named hardening follow-up). Evidence: [2026-10-19-home-injection-coexistence.md](../evidences/2026-10-19-home-injection-coexistence.md).
