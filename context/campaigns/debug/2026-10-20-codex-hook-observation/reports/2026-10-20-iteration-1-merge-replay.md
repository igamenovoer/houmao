# Iteration 1 Report: Codex Hook Capture, Trust, and Merge Replay

Date: 2026-10-20. Campaign: [debug-intent.md](../debug-intent.md). Iteration: [plan 1](../iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md). Status: iteration 1 complete; KQ-1 through KQ-5 resolved.

## Scope and lane

Eleven primary live sessions plus two auxiliary cases were captured on codex-cli 0.163.0 through the `codex-openlux-auto` lane (the GAC lane was measured dead with HTTP 402 on the same day; one S0-GAC run is retained as a superseded fault case). Every session has a paired hook stream, 5 fps pane recording, filled labels, and an evidence doc. All captures are under `tmp/codex-hook-capture/`; the dated narrative is in `evidences/`.

## E1: Auto-trust and injection

| Variant | Outcome | Evidence |
| --- | --- | --- |
| Bypass flag + `hooks.json` | Works unattended. Composer reached in 0.66 s with zero keypresses, no trust modal; `SessionStart`/`UserPromptSubmit`/`Stop`/`SessionEnd` all delivered. Chosen only as a fallback/experiment lane because it depends on a dangerous flag. | [S0 openlux](../evidences/2026-10-20-s0-gate-smoke-openlux.md) |
| Pre-written `[hooks.state."<key>".trusted_hash]`, no bypass | Works unattended with no trust modal; perturbing only the `SessionStart` command produces `1 hook is new or changed.` and blocks execution. Chosen for the managed path. Codex's own trust-all writes 12 entries whose hashes match `hash_hook.py` exactly (12/12); `PreModelRequest`/`PostModelRequest` are outside the review set. | [T1](../evidences/2026-10-20-t1-pretrusted-hash.md), [S2](../evidences/2026-10-20-s2-trust-control-and-interactive.md) |
| `-c hooks.<Event>=[...]` session flags | Works with the bypass flag; no `hooks.json` exists in the scratch home. Composable injection surface, but not an auto-trust mechanism by itself. Managed canonicalization does not strip `hooks.*` (source-derived). | [T2](../evidences/2026-10-20-t2-session-flags.md) |
| No bypass, no pre-trust (control) | Blocking `Hooks need review` selection modal; unattended sessions hang and receive zero hook events. `d` is not a valid deny key for the sandbox-escalation modal; Escape cancels and aborts the turn. | [S2](../evidences/2026-10-20-s2-trust-control-and-interactive.md) |

**E1 decision:** pre-write `[hooks.state]` into the runtime-home `config.toml` (user layer) for the managed path. It survives a launcher profile refresh; Codex's own trust-all writes to the active profile file, which a `--refresh-profile` would clobber. Keep `--dangerously-bypass-hook-trust` as a tested fallback, and `-c` as an experimental/composable surface.

## E2: Collector transport

The loopback HTTP collector plus the silent command-hook emitter delivered every live event with `via: http`; the emitter always exited 0 with empty stdout, and the file fallback is exercised only in the G0 self-test. No provider-side modification was needed. This is the chosen transport.

Evidence: all run roots under `tmp/codex-hook-capture/*/run-*/collector/events.ndjson`; harness self-test (`run_capture.py --self-test`) covers collector auth, heartbeat, emitter HTTP and file fallback.

## E3: Normalizer

Chosen mapping:

- `SessionStart` → presence; `source` distinguishes `startup`, `resume`, `compact`.
- `UserPromptSubmit` → busy; `turn_id` is the turn epoch; same-turn second prompt is a steer.
- `PreToolUse`/`PostToolUse` → activity, paired by `tool_use_id`.
- `PermissionRequest` → blocked, paired to the immediately preceding `PreToolUse` (no `tool_use_id` on the request; `tool_input` adds a `description`).
- `Stop` → success latch; `stop_hook_active=true` would mean continuation (defensive, never observed).
- `Interrupt` → interrupted, including the deny-cancel path.
- `PreCompact`/`PostCompact` → maintenance window; `SessionStart(compact)` → compaction boundary.
- `SessionEnd` → presence lost; open turn → terminal gap.
- `PreModelRequest`/`PostModelRequest` → counted unsupported no-ops at 0.163.0.
- `SubagentStart`/`SubagentStop` → counted but never observed in the matrix.

Evidence: [payload catalog](../evidences/2026-10-20-codex-hook-payload-catalog.md), [S1](../evidences/2026-10-20-s1-normal-multiturn.md), [S3](../evidences/2026-10-20-s3-permission-lane.md), [S4](../evidences/2026-10-20-s4-compaction.md).

## E4: Merge replay

`scripts/explore/codex-hook-observation/replay_reduce.py` is a standalone stdlib reducer that replays each `collector/events.ndjson` using the stream's own monotonic timestamps. It implements the archived three-axis model with the Codex amendments below. Synthetic self-tests cover normal turn, blocked-allow, blocked-deny, compaction window, terminal gap, steer, `stop_hook_active`, and unavailable model-request events.

Run matrix result: **PASS**, all 11 primary runs plus the S2-control and S0-GAC auxiliary cases. Every stream-shape/final-state expectation passed; every hook-observable label window passed. Pre-channel labels (`ready` before the first turn) and TUI-only trust labels are reported as n/a because the hook channel cannot see them.

| Run | Events | Final hook state | Labels |
| --- | --- | --- | --- |
| S0 | 4 | lost / ready / success | 1 OK, 1 n/a (pre-channel) |
| S1 | 8 | lost / ready / success, 2 epochs | 3 OK |
| S2-interactive | 4 | lost / ready / success | 1 OK, 2 n/a (TUI trust) |
| S3 | 11 | lost / ready / interrupted, allow+deny | 3 OK |
| S4 | 11 | lost / ready / success, 1 compaction | 3 OK |
| S5 | 4 | lost / ready / interrupted | 2 OK |
| S6 | 5 | lost / ready / success, 1 steer | 2 OK |
| S7 | 8 | lost / ready / success, 2 generations, same session_id | 3 OK |
| F1 | 2 | lost / unknown / none, terminal gap | 2 OK |
| T1 | 4 | lost / ready / success | 1 OK, 2 n/a (pre-channel + TUI trust) |
| T2 | 4 | lost / ready / success | 2 OK |
| S2-control (aux) | 0 | unknown / unknown / none | n/a (TUI trust) |
| S0-GAC (aux) | 3 | lost / unknown / none, session-end gap | 2 OK, 1 n/a (pre-channel) |

Full replay log: `tmp/codex-hook-capture/replay-all.log`; per-event timelines: `tmp/codex-hook-capture/replay-all-timeline.log` (206 lines, zero mismatches).

## KQ-5 P5.5 amendments (dated 2026-10-20)

1. **`turn_id` replaces the time-window correlation.** Same-turn second prompt = steer, not a queued turn; no FIFO queue at 0.163.0. Evidence: S1, S6, S7.
2. **Deny aborts the turn.** Pair `PermissionRequest` to the preceding `PreToolUse`; allow settles on the same-`tool_use_id` `PostToolUse`; deny settles on `Interrupt` with no `PostToolUse` and no `Stop`. Evidence: S3, KQ-4.
3. **Compaction is explicit.** `PreCompact`/`PostCompact` hold posture; the compaction operation has its own `turn_id`; `SessionStart(compact)` arrives at the next turn start; the post-compact turn gets a new epoch. The `silent_abort_idle` TUI heuristic is not needed. Evidence: S4.
4. **Model-request events are unavailable.** Treat `PreModelRequest`/`PostModelRequest` as counted no-ops; no token usage or model-request timing at 0.163.0. Evidence: catalog.
5. **Work axis has no Codex signal.** `Stop` lacks `background_tasks`; keep `work=unknown` or add a provider capability that lets `Stop` set `clear`; `settled` is otherwise unavailable. S6 steer is not background work. Evidence: S1/S6, catalog.
6. **Terminal-gap fallback.** Stream end with an open turn → presence lost, turn unknown, `last_turn=none`, `terminal_gap`; `SessionEnd` with an open turn is the same class. Collector heartbeat distinguishes agent death from collector failure. Evidence: F1, S0-GAC.
7. **`stop_hook_active` is a continuation, not a terminal.** Defensive rule; never observed live. Covered by the replay self-test.
8. **Generation/resume.** A new generation resets turn state; `SessionStart(resume)` re-establishes presence with the same `session_id`; the resumed turn gets a new `turn_id`. Evidence: S7.
9. **Pre-channel is unknown, not ready.** `SessionStart` is first-turn scoped; an untrusted/unanswered trust surface yields zero events. Do not infer ready or lost from hook silence alone. Evidence: S2 control, KQ-1.
10. **Permission payload detail.** `PermissionRequest.tool_input` adds a `description`; matchers/hash logic must not assume identical `tool_input` shapes. Evidence: S3.

## Campaign-level verdict

**The future `add-codex-hook-observation` change can proceed to proposal.** The capture matrix, trust/injection question, payload catalog, permission semantics, and merge replay are all resolved with dated evidence. The proposal must carry these conditions:

- Use `turn_id` correlation and steer semantics; do not port the Claude time-window/FIFO queue.
- Implement deny-aborts-turn blocked settling and the preceding-`PreToolUse` pair-back.
- Use `PreCompact`/`PostCompact` plus `SessionStart(compact)` for compaction boundaries; do not port the `silent_abort_idle` workaround.
- Pre-trust via `config.toml` `[hooks.state]` (user layer), not the active profile file.
- Do not promise `PreModelRequest`/`PostModelRequest` or token usage at 0.163.0.
- Decide the `work` axis policy for a provider without background-task signals.
- Include a managed-path integration test for `-c hooks.*` and for the `config.toml` pre-trust, since those interactions are source-derived, not live-tested through the managed launch policy.

## Links

- Key questions: [KQ-1](../key-questions/KQ-1-unattended-trust-injection.md), [KQ-2](../key-questions/KQ-2-event-availability-payloads.md), [KQ-3](../key-questions/KQ-3-delivery-semantics.md), [KQ-4](../key-questions/KQ-4-blocked-state-permission.md), [KQ-5](../key-questions/KQ-5-merge-semantics.md)
- Evidence: [S0 openlux](../evidences/2026-10-20-s0-gate-smoke-openlux.md), [S1](../evidences/2026-10-20-s1-normal-multiturn.md), [S2](../evidences/2026-10-20-s2-trust-control-and-interactive.md), [S3](../evidences/2026-10-20-s3-permission-lane.md), [S4](../evidences/2026-10-20-s4-compaction.md), [S5](../evidences/2026-10-20-s5-esc-interrupt.md), [S6](../evidences/2026-10-20-s6-queue-steer.md), [S7](../evidences/2026-10-20-s7-resume.md), [F1](../evidences/2026-10-20-f1-kill-fault.md), [T1](../evidences/2026-10-20-t1-pretrusted-hash.md), [T2](../evidences/2026-10-20-t2-session-flags.md), [payload catalog](../evidences/2026-10-20-codex-hook-payload-catalog.md)
- Replay: `scripts/explore/codex-hook-observation/replay_reduce.py`, `tmp/codex-hook-capture/replay-all.log`
