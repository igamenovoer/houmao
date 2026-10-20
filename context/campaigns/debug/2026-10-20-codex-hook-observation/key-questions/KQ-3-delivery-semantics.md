# KQ-3: Delivery Semantics

Status: resolved (iteration 1, 2026-10-20; named leftovers: hung-collector fault arm, async-loss arm). Owner: iteration 1. Campaign: [debug-intent.md](../debug-intent.md).

## Question

What collector transport and hook configuration delivers Codex hook events reliably to houmao, given Codex's execution semantics (sync/async, stdout hazards, timeouts, shutdown abort)?

Source baseline: hooks run via `<shell> -c "<command>"` with stdin JSON and no trailing newline; sync handlers per event run concurrently and are awaited; `async = true` handlers are aborted at session shutdown; `SessionEnd` is forced sync with a 1-3 s cap; other events default to 600 s (`codex-rs/hooks/src/engine/command_runner.rs`, `dispatcher.rs`, `discovery.rs:841`).

## Propositions

### P3.1 Stdout-silent collector never disturbs the agent

A collector/emitter that always exits 0 with empty stdout produces zero visible disturbance: no injected model context on `SessionStart`/`UserPromptSubmit`, no failed-hook markers on `Stop`/`Interrupt`. Test: run S1 with a deliberately noisy hook variant (control) and the silent variant; diff agent-visible output.

### P3.2 Sync-with-short-timeout is the right default

Sync handlers with short explicit timeouts (proposal: 5 s for all events except `SessionEnd` at its 3 s cap) deliver all events without stalling the agent measurably, and a hung-collector fault recovers within the timeout. Test: S1 baseline; one fault arm with a sleeping collector records the agent-side stall duration and failure marker behavior.

### P3.3 Async loss at shutdown is quantified

`async = true` handlers scheduled near session end are aborted; measure how many terminal events (`Stop` of the last turn, `SessionEnd`) are lost with async vs sync in a clean-exit session. Test: paired S1-repeat arms differing only in `async`.

### P3.4 Ordering guarantees measured

Events from one turn arrive at the collector in dispatch order under sync handlers; record any reordering with concurrent sync handlers (same event, multiple handlers) and with mixed sync/async. Test: sequence analysis of S1/S6 streams.

### P3.5 SessionEnd delivery window

`SessionEnd` fires and is delivered on clean TUI exit (`/quit` or Ctrl-C twice, whichever the build uses), within its 3 s cap. Test: S1 and S7 record exit-path delivery; the kill arm of P2.5 records its absence.

## Answer

Iteration 1, 2026-10-20, codex-cli 0.163.0.

- **P3.1 confirmed.** Across 11 sessions and 73 events with a stdout-silent, exit-0 emitter there was zero visible agent disturbance: no injected context, no failed-hook markers, no provider warnings attributable to hooks. The noisy-hook control was not separately run (the silent contract is enforced by construction in the emitter and verified by assertion in the G0 self-test).
- **P3.2 partially confirmed.** Sync handlers with short timeouts (5 s; SessionEnd 2 s inside its 1-3 s clamp) delivered every event with no measurable agent stall (turn latencies comparable to unhooked probe behavior; PermissionRequest-to-PostToolUse blocked interval 457 ms dominated by human response time). The hung-collector fault arm (agent-side stall and recovery when a hook command sleeps past its timeout) is **not yet run** — named iteration-2 leftover.
- **P3.3 unanswered (named gap).** Async-loss-at-shutdown was not measured: the v1 configuration uses sync handlers throughout, per the source-derived warning that `codex exec` aborts async hooks at shutdown. If async variants are ever proposed, this arm must run first.
- **P3.4 confirmed.** Events arrive in dispatch order in every captured stream (sequence-verified against labeled turn boundaries in all runs); no reordering observed with a single sync handler per event. Multi-handler concurrency was not exercised (out of scope for the observer, which installs exactly one handler per event).
- **P3.5 confirmed.** `SessionEnd` was delivered on every clean exit (15 of 15: `/quit` in TUI sessions, both resume generations) within ~60-600 ms of the exit command, comfortably inside its 2 s configured timeout; it is absent only on `kill -9`, as designed.

Summary: the sync + short-timeout + stdout-silent collector contract is validated live; the two unresolved items (hung-hook fault, async loss) are named iteration-2 leftovers with their arms specified.

## Scope

Covers transport, timing, ordering, and failure behavior. Event availability is KQ-2. Evidence: `evidences/` links added as produced.
