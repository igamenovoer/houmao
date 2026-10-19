# KQ-1: Settings Injection and Event Availability

Status: resolved (iteration 1, 2026-10-19; P1.4 resolved by reframe with named raw-helper follow-up). Owner: iteration 1. Campaign: [debug-intent.md](../debug-intent.md).

## Question

Is a launch-owned `--settings` observer configuration honored by Claude Code in TUI mode at the installed version (2.1.303) and at the supported floor (2.1.296, if a side-by-side install is practical), and does the v1 event set fire from it?

## Propositions

### P1.1 `--settings` injection works in TUI mode

A session launched with an appended `--settings <observer.json>` loads the observer hooks without disturbing operator or managed-home settings, and `SessionStart` is delivered to the collector. Test: launch with observer settings, verify `SessionStart` arrives within the startup grace.

### P1.2 HTTP hooks are deliverable on loopback

`type: http` hooks POST to a `127.0.0.1` listener with a bearer token, within their timeout, for the v1 HTTP-delivered events. Test: count delivered vs expected events per session; record any event that never arrives over HTTP.

### P1.3 Command-hook fallback works for `SessionStart`

The stdlib emitter contract (stdin JSON, POST-or-file, exit 0, stdout silent) delivers `SessionStart` even if HTTP hooks are unsupported for it. Test: run S1 with a command-hook `SessionStart` handler and confirm delivery.

### P1.4 Conflicting `--settings` detection

If launch args already carry `--settings`, the channel must degrade rather than double-inject. Test: one launch with a pre-existing `--settings` and the observer appended; record actual provider behavior (last-wins, error, or merge).

## Answer

Iteration 1, 2026-10-19. Verdicts per proposition:

- **P1.1 confirmed.** `--settings <observer.json>` is honored in TUI mode at 2.1.303 and at the 2.1.296 floor; `SessionStart` arrived within 1 s of provider start in every session (15 s grace trivially met). No settings-validation rejection, no disturbance of operator state. Evidence: [S0 gate](../evidences/2026-10-19-s0-gate-smoke.md), [S1](../evidences/2026-10-19-s1-normal-multiturn.md), [floor S1 repeat](../evidences/2026-10-19-floor-2-1-296-s1-repeat.md).
- **P1.2 confirmed.** All 8 HTTP-delivered v1 events arrived over loopback with the `$HOUMAO_HOOK_TOKEN` env reference interpolated by the provider; zero 401/403 rejections across 9 hooked sessions; collector-side rejects (oversized/malformed) exercised only in the G0 self-test. Evidence: [S1](../evidences/2026-10-19-s1-normal-multiturn.md), [S3](../evidences/2026-10-19-s3-permission-lane.md), [S5](../evidences/2026-10-19-s5-background-work.md).
- **P1.3 confirmed.** `SessionStart` rides the command-hook emitter in every session, delivered via emitter POST to the collector (`via: http` at the collector), including mid-session starts (`source: compact` in S4, `source: resume` in S7). The file fallback was validated by the G0 self-test and never needed live. Evidence: [S4](../evidences/2026-10-19-s4-compaction.md), [S7](../evidences/2026-10-19-s7-queue-resume.md).
- **P1.4 resolved by reframe.** The original conflict test (observer `--settings` appended to launch args that already carry `--settings`) cannot occur on the managed path: reading `src/houmao/agents/launch_policy/` and `src/houmao/agents/realm_controller/launch_plan.py` shows managed claude launch plans build their arg lists from the resolved launch behavior plus policy/provider-generated args, with no operator-controlled extra-args passthrough (`extra_args` exists only on the codex headless backends). The real coexistence question behind P1.4, whether operator-authored hooks in the same settings file survive an observer merge, is answered live: yes, in the home-injection arm the operator hook kept firing (2 marker lines) alongside the full observer block. Two honest caveats: the raw operator-facing launch-helper CLI (`launch_policy/cli.py`) does append a `--` passthrough and the claude policy currently owns only `--dangerously-skip-permissions`, so a conflicting `--settings` via that raw helper would reach the provider unvalidated today; and with home-primary injection (Part B correction) the managed path no longer passes `--settings` at all. Evidence: [home-injection coexistence](../evidences/2026-10-19-home-injection-coexistence.md).

Summary: the launch-owned observer configuration works end to end at 2.1.303 and the 2.1.296 floor, both via session-scoped `--settings` and via the managed home's `settings.json`; the conflict rule degenerates on managed launches (no args passthrough) and raw-helper hardening is a named follow-up.

## Scope

Covers launch-time injection and event availability only. Payload contents are KQ-3; merge behavior is KQ-5. Evidence: `evidences/` links added as produced.
