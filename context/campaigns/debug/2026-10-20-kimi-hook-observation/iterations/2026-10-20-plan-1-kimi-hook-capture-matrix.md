# Iteration Plan 1: Kimi Hook Capture Matrix

Status: capture and replay phases complete (2026-10-20). Date: 2026-10-20. Campaign: [debug-intent.md](../debug-intent.md).

Questions owned: [KQ-1](../key-questions/KQ-1-config-injection-coexistence.md), [KQ-2](../key-questions/KQ-2-event-availability-payloads.md), [KQ-3](../key-questions/KQ-3-delivery-semantics.md), [KQ-4](../key-questions/KQ-4-blocked-state-permission.md). [KQ-5](../key-questions/KQ-5-merge-semantics.md) replays these captures in this iteration's replay phase.

## Question / Answer Sought

Can houmao inject observer hooks into a kimi launch such that they execute with zero user action in unattended `--auto` TUI mode, and what do the 20 event payloads actually contain at the installed version? Deliverable: at least 5 (target 12) paired captures (hook stream + pane recording + labels) covering the campaign matrix, an injection verdict per E1 variant, a transport verdict for E2, and a payload catalog. The replay phase then replays the archived merged state-transition rules against the captured streams (E3/E4).

## Frozen Workload

- Host kimi: 2.2.0 (`kimi --version`, verified 2026-10-20), invoked directly (no houmao managed launch); no model argument is passed (the seeded config's `default_model` applies). The wrapper exports `KIMI_CODE_NO_AUTO_UPDATE=1` for version pinning. The in-session bootstrap check verifies the provider responds (any turn completes with a `Stop` event) and the session reaches the ready composer; stop and consult if auth fails.
- Workloads: throwaway git-less directories under `tmp/kimi-hook-capture/<scenario>/`; pane recording at 5 fps via the repo's terminal-record tooling; hook capture via the iteration-1 harness in `scripts/explore/kimi-hook-observation/`.
- Each session uses an isolated scratch `KIMI_CODE_HOME` seeded by copying `config.toml`, `credentials/`, `oauth/`, `device_id` from the operator's real `~/.kimi-code` at runtime (`cp` inside runner scripts; contents never enter chat or evidence docs). The real home is never modified.
- Frozen prompts per session (exact text in the arms table below); no improvisation mid-run.
- Cost discipline per the intent's credential and cost lane: short prompts, recordings reused across all arms, no sessions beyond this plan. T1, S2, and H1's mid-session phase cost zero tokens (no model call).
- Credential hygiene: runner scripts copy/read credentials at runtime; keys are never printed, copied into evidence docs, or embedded in artifacts.

## Predeclared Arms

| Session | Launch | Frozen prompt / actions | Predeclared expectation |
| --- | --- | --- | --- |
| S0 (gate) | scratch `KIMI_CODE_HOME` + 20-event `[[hooks]]`, `kimi --auto` in tmux | "Reply with exactly: OK" | `SessionStart(source=startup)` arrives awaited at create (timing recorded vs codex's lazy dispatch); `UserPromptSubmit` + `Stop`; ready composer reached with zero keypresses; no modal/prompt surfaces |
| S1 normal | as S0 | "Reply with exactly: OK", then "Run the shell command `echo hi` and report its output, then reply with exactly: DONE" (forces `Bash` path); hold session ≥65 s; fold in H1: append marker `[[hooks]]` (`UserPromptSubmit` → `touch <run>/hot-reload-marker`) mid-session before a third short prompt "Reply with exactly: OK" | full turn cycle x3; `tool_call_id` pairing; heartbeat cadence + `uptime_ms`; marker hook does NOT fire mid-session (load-once); `SessionEnd(reason=exit)` on clean exit |
| S2 malformed control | scratch home + hooks block where ONE entry has an extra key `cwd = "/tmp"` | "Reply with exactly: OK" | entire hooks section dropped (zero events collected); warning visibility recorded (TUI surface + a paired `kimi -p` stderr probe); session otherwise normal |
| S3 permission | scratch home + hooks, NO `--auto` (default ask mode) | "Create a file named /tmp/houmao-kimi-hook-allow.txt containing hello" (driver approves at prompt), then "Create a file named /tmp/houmao-kimi-hook-deny.txt containing hello" (driver denies) | `PermissionRequest` before modal paint; `PermissionResult(decision=approved\|rejected)`; `tool_call_id` pairing; deny-path settle events recorded (whatever they are) |
| S4 compaction | as S0 | "Read the file README.md in the current directory and summarize it in one sentence." (workdir gets a small README.md), then `/compact` via send-keys, then "Reply with exactly: OK" | `PreCompact`/`PostCompact(trigger="manual")` with token-count fields; posture continuity across compaction |
| S5 interrupt | as S0 | "Write a long essay about recursion." then Esc mid-generation | `Interrupt(turn_id, reason="cancelled")` fires; `Stop` does NOT fire for the aborted turn |
| S6 queue + steer | as S0 | "Write a long essay about queues." then type "Reply with exactly: OK" while busy | `UserPromptQueued(prompt_id, queue_length)`; drain ordering; `is_steer` on the eventual `UserPromptSubmit`; one or two `Stop`s recorded as observed |
| S7 resume + hot-reload | as S0; clean exit; relaunch `kimi --continue` on the same scratch home (config edited between generations per H1) | "Reply with exactly: OK" before exit; "Reply with exactly: OK" after resume | `SessionStart(source="resume")`; session_id semantics across generations; the H1 marker hook fires only in the resumed generation |
| S8 headless | `KIMI_CODE_HOME=<scratch> kimi -p` (no tmux, no pane recording; stderr captured) | `-p "Reply with exactly: OK"` | hooks fire in print mode (`SessionStart`, `UserPromptSubmit`, `Stop`, `SessionEnd` expected; no permission events under print-mode forced auto) |
| F1 fault | as S0, mid-turn `kill -9` the kimi process tree | "Write a long essay about faults." then kill mid-turn | exactly which events do NOT arrive (no `Stop`/`Interrupt`/`SessionEnd`); heartbeat cessation; terminal-gap signature |
| D1 transport fault | as S0; collector killed after `SessionStart` | "Reply with exactly: OK" | emitter file fallback engages; session unaffected (fail-open); fallback ordering via emitter sequence |
| T1 slow-hook | scratch home + hooks where `SessionStart` and `SessionEnd` commands prepend `sleep 3`; | launch, wait ready, exit (zero model cost; one "Reply with exactly: OK" only if needed to settle) | time-to-ready delayed ~3 s vs S0 baseline; exit delayed ~3 s; delays recorded |
| S9 subagent (optional) | as S0 | "Use the Agent tool to launch a subagent that replies with exactly: OK" | `SubagentStart`/`SubagentStop(agent_name)`, `TaskStarted(kind="agent")`; skip if cost or tooling friction appears; name as leftover if skipped |

## Harness Build (pre-capture, part of this iteration)

- [x] `scripts/explore/kimi-hook-observation/kimi_hooks.py`: generates the scratch home's `config.toml` merge — 20 events, one `[[hooks]]` entry each, matcher omitted, timeout 5 s, command = `<pixi python> <abs emit_hook.py>` shell-quoted; validates the written file by strict read-back (tomllib parse + per-entry key whitelist `{event, matcher, command, timeout}` + event-name enum), failing loudly before any launch (the P1.2 failure mode must be caught by the installer, not discovered dead)
- [x] `scripts/explore/kimi-hook-observation/collector.py`: stdlib loopback collector (bearer token, sequence stamping, append-only `events.ndjson`, `collector.json` heartbeat); port from the Codex lane if it ports cleanly, else rewrite
- [x] `scripts/explore/kimi-hook-observation/emit_hook.py`: command-hook emitter (stdin JSON -> POST-or-file, exit 0, stdout silent); same porting rule
- [x] `scripts/explore/kimi-hook-observation/run_capture.py`: one-command scenario runner (seed scratch `KIMI_CODE_HOME` by `cp` from `~/.kimi-code`, tmux launch with the arm's flags, drive frozen prompt/actions tracker-blind, pane record at 5 fps, labels template, `launch.json` manifest); includes the provider-free `--self-test` gate G0
- [x] `scripts/explore/kimi-hook-observation/README.md`: harness usage and layout
- [x] `scripts/explore/kimi-hook-observation/replay_reduce.py` (replay phase): stdlib replay reducer over captured `events.ndjson` -> merged posture timeline, expectation checks, label checks, synthetic `--self-test`, full-matrix `--all` — built and passing (12/12 self-test checks; 18 roots / 113 events; 21 label checks OK, 20 n/a, 0 mismatches)

## Gates (checked in order; a failed gate stops the iteration)

- [x] G0 harness: **PASS** (`--self-test`, 19/19 checks; duplicate entry validates; malformed entry refused; emitter stdout empty on success and fallback paths)
- [x] G1 S0 smoke: **amended 2026-10-20 and PASSED** (see [S0 gate smoke](../evidences/2026-10-20-s0-gate-smoke.md)). Amendment (2026-10-20 correction): the pre-prompt `SessionStart` requirement is removed because kimi 2.2.0's TUI creates the session lazily on the first message. G1 now passes iff (a) the ready composer is reached within 15 s of launch with zero keypresses, (b) after the driver sends the frozen prompt `Reply with exactly: OK`, `SessionStart(source=startup)` arrives within 15 s of the prompt and no later than the matching `UserPromptSubmit`/`Stop` sequence for that turn, and (c) the turn completes with `Stop`. `SessionStart` is still awaited at session creation; creation is just deferred to the first message. The original criterion is recorded as refuted: zero events in 25 s after launch in `tmp/kimi-hook-capture/s0/run-20261020T132548Z/`.
- [x] G2 injection honored: **PASS**. Every exercised event family produced events; silent families are named: `StopFailure` (never forced), `TaskStarted` (Agent tool emitted none), `Notification` (no background task), permission events absent under `--auto` (expected positive control), `SessionEnd` absent in headless print mode.
- [x] G3 pairing: **PASS**. Every TUI capture has a 5 fps pane recording + hook stream + labels with matching monotonic/UTC time base; S2 has pane + empty stream + labels by design; S8 is headless with no pane (stdout/stderr instead), recorded as an exception.

## Measurements and Decision Rules

- Per-event delivery latency (pane-visible cause frame vs collector receipt, monotonic clock), per-session event sequence dump, payload field inventory per event type, diffed against the source-derived catalog.
- KQ-1 resolved when S0/S2/S1+S7(H1) and the P1.4 config diffs each give a recorded verdict: the merge shape runs all hooks unattended, the malformed and hot-reload failure modes are documented, and the coexistence diff is clean.
- KQ-2 catalog built from all captures; absent/extra fields named per event; `tool_call_id` grouping verified against labeled tool calls; permission absence under `--auto` recorded as positive control evidence.
- KQ-3 answered from all runs (P3.1), D1 (P3.2), T1 (P3.3), self-test (P3.4/P3.5).
- KQ-4 answered from S3 and S5; if P4.5 cannot be forced cheaply it is named unresolved.
- KQ-5 answered in the replay phase: `replay_reduce.py` over every captured run against the archived rules; each rule demonstrated or named unresolved with the missing evidence.

## Execution Checklist

- [x] Build harness (items above, minus replay_reduce) — Phase A, G0-passed
- [x] G0 self-test
- [x] S0 gate session — amended G1 **PASS** (session-less startup; `SessionStart` 0.238 s after prompt, before UPS/Stop)
- [x] S1-S8 + F1 + D1 + T1 captures in order, each with labels written same-day
- [x] Optional S9 — captured (`SubagentStart`/`SubagentStop`; no `TaskStarted`)
- [x] Payload catalog written to `evidences/2026-10-20-kimi-hook-payload-catalog.md`
- [x] KQ-1..KQ-4 answer sections updated with evidence links — all propositions confirmed except P4.5 (`StopFailure`) and named partials
- [x] Replay phase: `replay_reduce.py` built, `--self-test` synthetic checks pass (12/12), full-matrix replay run (`--all` PASS: 18 roots, 113 events, 0 label mismatches), KQ-5 answered, synthesis report written to `reports/2026-10-20-kimi-hook-observation-synthesis.md`

## Result

Capture phase complete on 2026-10-20: **13 arms / 16 process launches** (S6 and F1 each needed a corrected or extended second run; S7 has two generations). Every core arm passed its predeclared expectation except where the live surface corrected the expectation itself: `TaskStarted` does not fire for the Agent tool, headless print mode emits no `SessionEnd`, plain Enter while busy does not queue, and the TUI's session-less startup moved `SessionStart` from process launch to first-message creation. The amended G1 passed (ready 3.219 s; `SessionStart` 0.238 s after the prompt, before `UserPromptSubmit`/`Stop`).

| Arm | Run root | Verdict | Evidence |
| --- | --- | --- | --- |
| S0 gate | `tmp/kimi-hook-capture/s0/run-20261020T133111Z/` | **PASS (amended G1)**; 21-entry dedup probe: exactly 1 UPS | [S0 gate smoke](../evidences/2026-10-20-s0-gate-smoke.md) |
| S1 normal | `tmp/kimi-hook-capture/s1/run-20261020T133343Z/` | **PASS**: 3 turns, Bash pair, heartbeat 60 s/60001 ms, H1 marker absent | [S1 normal](../evidences/2026-10-20-s1-normal-multiturn.md) |
| S2 malformed | `tmp/kimi-hook-capture/s2/run-20261020T133534Z/` | **PASS control**: whole hooks section dropped; TUI silent; `-p` stderr warning | [S2 malformed control](../evidences/2026-10-20-s2-malformed-control.md) |
| S3 permission | `tmp/kimi-hook-capture/s3/run-20261020T133622Z/` | **PASS**: approved + rejected, keys `1`/`Escape`, labels recorded | [S3 permission lane](../evidences/2026-10-20-s3-permission-lane.md) |
| S4 compaction | `tmp/kimi-hook-capture/s4/run-20261020T133716Z/` | **PASS**: Pre/PostCompact(manual), 7.224 s, fresh turn_id 1 | [S4 compaction](../evidences/2026-10-20-s4-compaction.md) |
| S5 interrupt | `tmp/kimi-hook-capture/s5/run-20261020T133804Z/` | **PASS**: Interrupt(cancelled), no Stop | [S5 interrupt](../evidences/2026-10-20-s5-interrupt.md) |
| S6 queue/steer | `tmp/kimi-hook-capture/s6/run-20261020T134110Z/` (canonical) | **PASS with key correction**: Ctrl-S → `UserPromptQueued(queue_length=1)`, no second UPS/Stop; plain-Enter run `run-20261020T133838Z` recorded as deviation | [S6 queue/steer](../evidences/2026-10-20-s6-queue-steer.md) |
| S7 resume | `tmp/kimi-hook-capture/s7/run-20261020T134720Z/` | **PASS**: `SessionStart(resume)` before prompt, same session id, H1 marker fires after restart | [S7 resume](../evidences/2026-10-20-s7-resume-hot-reload.md) |
| S8 headless | `tmp/kimi-hook-capture/s8/run-20261020T134807Z/` | **PASS with a named gap**: four turn events fire; **no `SessionEnd`** | [S8 headless](../evidences/2026-10-20-s8-headless.md) |
| F1 SIGKILL | `tmp/kimi-hook-capture/f1/run-20261020T134947Z/` (canonical; prior `134906Z`) | **PASS**: no settle events in 70 s, no heartbeat ever fired, terminal gap | [F1 terminal gap](../evidences/2026-10-20-f1-sigkill-terminal-gap.md) |
| D1 transport | `tmp/kimi-hook-capture/d1/run-20261020T135119Z/` | **PASS**: SS HTTP, turn+end fallback, emitter_seq 2-5 increasing | [D1 transport fault](../evidences/2026-10-20-d1-transport-fault.md) |
| T1 slow hooks | `tmp/kimi-hook-capture/t1/run-20261020T135150Z/` | **PASS**: SS +3.007 s, exit +3.016 s, ready unaffected (corrected premise) | [T1 slow lifecycle](../evidences/2026-10-20-t1-slow-lifecycle.md) |
| S9 subagent (optional) | `tmp/kimi-hook-capture/s9/run-20261020T135227Z/` | **PASS with a named gap**: SubagentStart/Stop captured; no TaskStarted | [S9 subagent](../evidences/2026-10-20-s9-subagent.md) |

### Replay Phase Result (2026-10-20)

`replay_reduce.py` reduced all 18 campaign run roots (14 with hook streams, 4 empty controls; 113 events) and matched every declared stream shape and final posture. 21 label checks passed, 20 were `n/a` (unfilled `unknown` expectations, headless/no-pane labels, and pre-channel windows), 0 mismatched. The 17 harness G0 roots under `tmp/kimi-hook-capture/self-test/` are detected as non-campaign streams and named as skipped. `--self-test` passed 12/12 synthetic checks. First replay exposed one prose error, not a reducer error: S7 generation 2 starts at `turn_id=1`, not 0; the catalog and S7 evidence were corrected the same day. Full per-proposition answers and the E1-E4 settled variants are in [KQ-5](../key-questions/KQ-5-merge-semantics.md) and the [synthesis report](../reports/2026-10-20-kimi-hook-observation-synthesis.md).

| Replay scope | Verdict |
| --- | --- |
| `--self-test` (normal, blocked-allow, blocked-deny, compaction, interrupt, terminal gap, resume-generation, headless, queue, subagent, fallback ordering, fallback loader) | **PASS 12/12** |
| `--all` campaign matrix | **PASS**: 18 roots, 113 events, 0 expectation mismatches, 0 label mismatches |
| KQ-5 P5.1-P5.5 | All confirmed; P5.1 carries the S7 `turn_id` correction, P5.4 is the idle-window case |
| E1-E4 | Settled: TOML append + strict read-back; HTTP + file fallback; order/scope normalizer; kimi transition rules |

### Gates

| Gate | Verdict |
| --- | --- |
| G0 harness | PASS (19/19 self-test checks) |
| G1 S0 amended | PASS (all five checks) |
| G2 injection honored | PASS; silent families named (`StopFailure`, `TaskStarted`, `Notification`, permission under `--auto`, headless `SessionEnd`) |
| G3 pairing | PASS; every TUI arm has pane recording + hook stream + labels on the shared monotonic clock; S8 is the headless exception |

### Harness Corrections Recorded During Capture (2026-10-20)

1. **Readiness for inline layout**: `composer_ready()` scans the whole pane, not the last 10 lines; the ready surface is top-anchored (S0 attempts 1-2 were false negatives).
2. **Amended G1 ordering**: `run_s0()` submits the frozen prompt, then requires `SessionStart` within 15 s and checks `source=startup` plus event order.
3. **All fresh-session arms prompt-first**: S1/S3/S4/S5/S6/S7/S9 now create the session with their frozen first prompt before requiring `SessionStart`; S7 resumes pre-prompt because `--continue` creates at launch.
4. **S6 key sequence**: second input changed from Enter to `C-s`; plain Enter does not emit `UserPromptQueued`.
5. **F1 observation window**: extended from 12 s to 70 s to cover the 60 s heartbeat due.
6. **T1 measurement and cost**: one OK prompt is required to create the session; the predeclared zero-cost/ready-delay premise was corrected (ready is unaffected; session-create and exit are delayed).
7. **D1 kill timing**: waits for `SessionStart` with a 50 ms poll, then kills the collector; because the prompt creates the session, the kill lands between SS and UPS and the whole turn is fallback.

### Remaining Unknowns

- `StopFailure` (P4.5): never forced; needs a controlled turn-level failure.
- `TaskStarted(kind=agent)` and `Notification(task.*)`: not emitted in the exercised Agent flow / no background task.
- `is_steer=true` and `PermissionResult` values `cancelled`/`error`: not exercised.
- P1.4 reverse order (launch-policy field write after the hook block) not exercised.
- Pane-cause-to-collector latency is bounded by the 5 fps recorder, not measured to the millisecond.
- Compaction during an armed/active turn (budget/overflow trigger) not exercised; S4 compacted from `ready`.
- Background subagent outliving the parent turn, `SubagentStop` without a nested `Stop`, `SessionStart` sources `clear`/`fork`/`compact`, and `SessionEnd` reasons other than `exit` not exercised.
- Heartbeat-derived liveness is unavailable for sessions shorter than the first 60 s tick (F1), quantified in KQ-5.

### Replay Corrections Recorded (2026-10-20)

1. **S7 `turn_id` continuity**: generation 2's first `TurnStarted` carries `turn_id=1`; the session-scoped counter continues across `--continue`. The capture note and payload catalog said 0 and were corrected; the replay expectation is `(0, 1)`.
2. **S6 label windows**: label timestamps are 1 s-granular and the blocked/settle rows can sit just outside a window; the reducer applies a 3 s lookbehind/lookahead and stops lookahead at a new `UserPromptSubmit` or a new-generation `SessionStart`. No label mismatch remained after this rule.

### Next Phase

Campaign closed on 2026-10-20: replay and synthesis are complete. The future `add-kimi-hook-observation` OpenSpec change consumes [KQ-5](../key-questions/KQ-5-merge-semantics.md) and the [synthesis report](../reports/2026-10-20-kimi-hook-observation-synthesis.md); the named leftovers need new live evidence, not another replay of these captures.

