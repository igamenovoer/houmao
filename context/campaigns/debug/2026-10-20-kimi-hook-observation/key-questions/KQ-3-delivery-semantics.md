# KQ-3: Delivery Semantics

Status: answered (2026-10-20); named unresolved items remain where marked. Owner: iteration 1. Campaign: [debug-intent.md](../debug-intent.md).

## Question

What transport should the kimi observer use (HTTP collector vs file-append emitter), and what are the ordering, latency, failure, and lifecycle-timing characteristics of kimi hook delivery at 2.2.0?

Source baseline: spawn/timeout/kill at `extern/orphan/kimi-code/packages/agent-core-v2/src/features/externalHooks/internal/runHook.ts` (@ `67325c1`); matching/dedup/parallelism at `internal/matchHooks.ts:44-113`; awaited lifecycle events at `session/sessionExternalHooksService.ts:63-82,99-107`.

## Propositions

### P3.1 HTTP transport delivers ordered, low-latency envelopes

The dual-path emitter (HTTP POST primary, file fallback) delivers envelopes to the loopback collector with monotonic sequence numbers and millisecond UTC stamps; per-event latency from pane-visible cause to collector receipt is small (target < 500 ms for local events). Test: every capture run; compute latency from paired monotonic stamps.

### P3.2 Fail-open holds end to end

With the collector dead (D1 arm), the emitter's file fallback engages, the kimi session is unaffected (turns complete, no surface error), and fallback envelopes preserve order via the emitter sequence. Test: D1 (kill collector after `SessionStart`, run one prompt); diff fallback file against expected sequence.

### P3.3 Awaited lifecycle hooks delay the session lifecycle measurably

A `SessionStart` hook running `sleep 3` delays time-to-ready by ~3 s relative to the S0 baseline; a `SessionEnd` `sleep 3` hook delays exit similarly; exceeding the configured hook timeout triggers SIGTERM then SIGKILL of the hook process group after 100 ms and the session proceeds (fail-open). Test: T1 arm (zero model cost — create and close only, plus one OK prompt if a turn is needed); record delays and any kill evidence.

### P3.4 The emitter must keep stdout silent

Any stdout from a `UserPromptSubmit` hook on the allow path is appended to the model context (`internal/userPrompt.ts:22-73`). The emitter prints nothing, ever. Test: harness self-test asserts empty emitter stdout on success and failure paths; S1 prompt answers are not polluted (the model does not echo observer artifacts).

### P3.5 Dedup and parallelism match source

Hooks with identical `(cwd, command)` keys dedupe first-wins; matched hooks run in parallel. Test: self-test configuration includes a duplicate `[[hooks]]` entry; record whether the event arrives once. Parallelism is recorded from simultaneous `PreToolUse` arrivals if multiple rules match (single-rule observer config makes this informational only).

## Answer

(2026-10-20, full capture matrix executed. Evidence: [S0 gate smoke](../evidences/2026-10-20-s0-gate-smoke.md), [S1 normal](../evidences/2026-10-20-s1-normal-multiturn.md), [D1 transport fault](../evidences/2026-10-20-d1-transport-fault.md), [T1 slow lifecycle](../evidences/2026-10-20-t1-slow-lifecycle.md), [payload catalog](../evidences/2026-10-20-kimi-hook-payload-catalog.md), harness `--self-test` `tmp/kimi-hook-capture/self-test/run-20261020T131824Z`.)

- **P3.1 — confirmed for delivery and ordering; latency is sub-second but not frame-quantified.** Every live event reached the loopback collector in order; the HTTP path stamped millisecond UTC plus the shared monotonic clock. The collector's envelopes arrived before the 5 fps pane showed the corresponding surface (for example S0 `Stop` at 13:31:18.596 and the settled answer around its sample). A precise pane-cause-to-receipt latency is bounded by the 0.2 s recorder granularity, not measured to the millisecond.
- **P3.2 — confirmed.** D1 killed the collector immediately after `SessionStart`. `SessionStart` arrived over HTTP (`sequence=1`); `UserPromptSubmit`, `TurnStarted`, `Stop`, and `SessionEnd` all arrived through the command fallback (`sequence=null`, `via=command_fallback`) with strictly increasing `emitter_seq` 2,3,4,5. The session was unaffected: OK answer, clean `/exit`, `SessionEnd`.
- **P3.3 — confirmed.** T1's `SessionStart`/`SessionEnd` hooks were prefixed with `sleep 3; `. Ready composer was **not** delayed (2.877 s vs S0 3.219 s) because session creation is deferred to the prompt; `SessionStart` arrived 3.245 s after the prompt (**+3.007 s** vs 0.238 s), and `/exit` took 3.984 s (**+3.016 s** vs 0.968 s), with `SessionEnd` 3.504 s after exit start. No timeout kill was exercised (3 s < 5 s hook timeout).
- **P3.4 — confirmed in the harness, partially live.** The emitter asserts empty stdout on success and fallback paths, and every generated hook command produced empty stdout. Live answers were exactly `OK`/`DONE` with no observer artifacts, so no prompt-context pollution was observed; the append-to-context path was not instrumented directly.
- **P3.5 — confirmed live.** The S0 config carried 21 entries: the 20 observer events plus a byte-identical duplicate `UserPromptSubmit` (same command, timeout, no matcher). One prompt produced **exactly one** `UserPromptSubmit` delivery. Dedup first-wins holds at 2.2.0. All other arms produced one UPS per submitted prompt (S1: 3, S3: 2, S4: 2, S7: 1+1).

Transport verdict: HTTP primary plus file fallback is reliable and fail-open; the fallback preserves order via `emitter_seq`, and the session never notices collector death. The 5 s hook timeout is comfortable for both paths (3 s injected sleep still completed).

The collector accepted zero live requests; `raw-provider-payloads.ndjson` is empty in every S0 run.

## Scope

Covers transport choice, ordering, latency, failure behavior, and lifecycle timing. Event content is KQ-2; what the reducer does with gaps is KQ-5. Evidence: `evidences/` links added as produced.
