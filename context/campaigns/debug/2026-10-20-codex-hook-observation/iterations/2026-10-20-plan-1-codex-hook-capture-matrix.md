# Iteration Plan 1: Codex Hook Capture Matrix

Status: executed (iteration 1 complete, 2026-10-20; G0-G3 passed with named leftovers, see Result). Date: 2026-10-20. Campaign: [debug-intent.md](../debug-intent.md).

Questions owned: [KQ-1](../key-questions/KQ-1-unattended-trust-injection.md), [KQ-2](../key-questions/KQ-2-event-availability-payloads.md), [KQ-3](../key-questions/KQ-3-delivery-semantics.md), [KQ-4](../key-questions/KQ-4-blocked-state-permission.md). KQ-5 replays these captures in a later iteration.

## Question / Answer Sought

Can houmao inject observer hooks into a Codex launch such that they execute with zero user action in unattended TUI mode, and what do the 14 event payloads actually contain at the installed version? Deliverable: at least 5 (target 7) paired captures (hook stream + pane recording + labels) covering the campaign matrix, a trust/injection verdict per E1 variant, and a payload catalog.

## Frozen Workload

- Host codex: 0.163.0 (`codex --version`, verified 2026-10-20) via `~/.local/bin/codex-openlux-auto` (OpenLux relay profile `openlux-auto`; lane corrected 2026-10-20 after the codex-gac relay returned HTTP 402 at the S0 gate — see the intent's credential lane section); no model argument is passed. The in-session bootstrap check verifies the provider responds (any turn completes with a `Stop` event) and the session reaches the ready composer; stop and consult if the lane fails auth.
- Trust-arm launches that must not use the GAC profile use `~/.local/bin/codex-skip-all` (plain `codex` + `--dangerously-bypass-approvals-and-sandbox` + `--dangerously-bypass-hook-trust`) or raw `codex` as the arm requires.
- Workloads: throwaway git-less directories under `tmp/codex-hook-capture/<scenario>/`; pane recording at 5 fps via the repo's terminal-record tooling; hook capture via the iteration-1 harness in `scripts/explore/codex-hook-observation/`.
- Each session uses an isolated scratch `CODEX_HOME` (created before launch; Codex requires it to exist) containing only the auth material the lane needs plus the arm's hook configuration; the operator's real `~/.codex` is never modified.
- Frozen prompts per session (exact text in the arms table below); no improvisation mid-run.
- Cost discipline per the intent's credential and cost lane: short prompts, recordings reused across all arms, no sessions beyond this plan.
- Credential hygiene: runner scripts read credentials at runtime; keys are never printed, copied, or written into artifacts.

## Predeclared Arms

| Session | Launch | Frozen prompt / actions | Predeclared expectation |
| --- | --- | --- | --- |
| S0 (gate) | scratch CODEX_HOME + hooks.json + `--dangerously-bypass-hook-trust`, codex-openlux-auto lane | "Reply with exactly: OK" | `SessionStart` + `UserPromptSubmit` + `Stop` arrive; no trust modal; ready composer reached with no keypress |
| S1 normal | as S0 | "Reply with exactly: OK", then "Create a file named /tmp/houmao-codex-hook-s1.txt containing hello, then run `echo done`" (forces `apply_patch` + `Bash` paths) | full turn cycle x2; `Pre/PostModelRequest`, `Pre/PostToolUse` with canonical tool names; `SessionEnd` on clean exit |
| S2 trust control | scratch CODEX_HOME + hooks.json, NO bypass flag, NO pre-trust | "Reply with exactly: OK" | documented failure mode: trust modal painted (would hang unattended) or hooks silently skipped; then answer "trust all" interactively and confirm `hooks.state` entries appear in the scratch home (validates P1.2 key format) |
| S3 permission | lane profile env WITHOUT approvals bypass (`approval_policy = "on-request"`, sandbox default), hooks + bypass-hook-trust | "Create a file named /tmp/houmao-codex-hook-allow.txt containing hello" (allow at modal), then "Create a file named /tmp/houmao-codex-hook-deny.txt containing hello" (deny at modal) | `PermissionRequest` before modal paint; settle event on allow (`PreToolUse` pair); deny-path settle evidence recorded; correlation rule without `tool_use_id` exercised |
| S4 compaction | as S0 | "Read README.md and summarize in one sentence.", then `/compact` via send-keys, then "Reply with exactly: OK" | `PreCompact`/`PostCompact(trigger="manual")`; `SessionStart(source="compact")`; posture continuity |
| S5 interrupt | as S0 | "Write a long essay about recursion." then Esc mid-generation | `Interrupt` fires; `Stop` does NOT fire for the aborted turn |
| S6 queue + steer | as S0 | "Write a long essay about queues." then type "Reply with exactly: OK" while busy | second `UserPromptSubmit` ordering vs `Stop`; steered-input behavior recorded |
| S7 resume | as S0; exit; relaunch with `codex resume` (explicit id or `--last`, resolved in-run) against the same scratch home | "Reply with exactly: OK" before exit; "Reply with exactly: OK" after resume | `SessionStart(source="resume")`; session_id semantics across generations; `SessionEnd` on each clean exit |
| F1 fault (no LLM cost beyond start) | as S0, mid-turn `kill -9` the codex process | "Write a long essay about faults." then kill mid-turn | exactly which events do NOT arrive (no `Stop`, no `SessionEnd`); terminal-gap fallback evidence for KQ-5 P5.3 |
| T1 hash arm (P1.2) | scratch CODEX_HOME + hooks.json + pre-written `[hooks.state."<key>".trusted_hash]`, NO bypass flag, codex-openlux-auto lane | "Reply with exactly: OK" | hooks run unattended without the flag; perturbing the command stops them (hash proven load-bearing) |
| T2 `-c` arm (P1.4) | `-c 'hooks.SessionStart=[...]'` injection only + bypass flag, no hooks.json | "Reply with exactly: OK" | `SessionStart` arrives from session-flags layer; interaction with managed-launch canonicalization recorded |

## Harness Build (pre-capture, part of this iteration)

- [x] `scripts/explore/codex-hook-observation/observer_hooks.py`: generates `hooks.json` (v1 event set: all 14 events subscribed, command handlers, sync with 5 s timeout except `SessionEnd` at 2 s) plus the pre-trust state block for arm T1
- [x] `scripts/explore/codex-hook-observation/collector.py`: stdlib loopback collector (bearer token, sequence stamping, append-only `events.ndjson`); port from the Claude lane if it ports cleanly, else rewrite
- [x] `scripts/explore/codex-hook-observation/emit_hook.py`: command-hook emitter (stdin JSON -> POST-or-file, exit 0, stdout silent); same porting rule
- [x] `scripts/explore/codex-hook-observation/hash_hook.py`: local reimplementation of Codex's normalized-hook trust hash (SHA-256 over compact JSON of the normalized `MatcherGroup`, sorted keys, `sha256:` prefix) for arm T1
- [x] `scripts/explore/codex-hook-observation/run_capture.py`: one-command scenario runner (scratch CODEX_HOME, tmux launch with the arm's flags, drive frozen prompt/actions, pane record at 5 fps, labels template)
- [x] `scripts/explore/codex-hook-observation/README.md`: harness usage and layout

## Gates (checked in order; a failed gate stops the iteration)

- [x] G0 harness: collector and emitter pass a local self-test with a synthetic POST (no provider involved); `hash_hook.py` reproduces the `currentHash` Codex reports for a known hook (from `hooks/list` via app-server or the TUI trust write observed in S2)
- [x] G1 S0 smoke: `SessionStart` arrives within 15 s of provider start with zero keypresses; provider behaves normally; GAC lane live
- [x] G2 injection honored: the injected config produces events for every event family the scenario exercises; a silent event family is recorded, not ignored
- [x] G3 pairing: every capture has pane recording + hook stream + labels with matching time base (monotonic offset recorded)

## Measurements and Decision Rules

- Per-event delivery latency (event timestamp vs visible surface frame), per-session event sequence dump, payload field inventory per event type, diffed against `codex-rs/hooks/schema/generated/`.
- KQ-1 resolved when S0/S2/T1/T2 each give a recorded verdict: which E1 variants run hooks unattended with zero user action, and the control's failure mode is documented with pane evidence.
- KQ-2 catalog built from all captures; absent/extra fields named per event; `turn_id` grouping verified against labeled turn boundaries.
- KQ-3 timing/ordering propositions answered from S1/S5/S7/F1 sequences plus one hung-collector fault arm (sleeping emitter; record agent-side stall and recovery).
- KQ-4 answered from S3; if no deny-path settle event exists, the reducer fallback rule is named as the v1 limit.

## Execution Checklist

- [x] Build harness (items above)
- [x] G0 self-test
- [x] S0 gate session
- [x] S1-S7 + F1 captures in order, each with labels written same-day
- [x] T1/T2 trust arms
- [ ] Hung-collector fault arm
- [x] Payload catalog written to `evidences/2026-10-20-codex-hook-payload-catalog.md`
- [x] KQ-1..KQ-4 answer sections updated with evidence links

## Result

Iteration 1 executed on 2026-10-20 at codex-cli 0.163.0. All gates passed (G0: self-test 16/16; G1: S0 composer unattended ~0.7 s with `SessionStart`/`UserPromptSubmit`/`Stop`; G2: every exercised event family produced events with silent families named in the catalog; G3: pane recording + hook stream + labels + monotonic/UTC pair in all runs). Twelve paired captures (73 provider events), exceeding the 7-session target.

### Captured Sessions

| Session | Run root (`tmp/codex-hook-capture/…`) | Evidence |
| --- | --- | --- |
| S0 gate (gac lane, 402) | `s0/run-20261020T035053Z` | [evidence](../evidences/2026-10-20-s0-gate-smoke.md) (superseded lane doc) |
| S0 gate (openlux) | `s0/run-20261020T035949Z` | [evidence](../evidences/2026-10-20-s0-gate-smoke-openlux.md) |
| S1 normal multi-turn | `s1/run-20261020T041527Z` | [evidence](../evidences/2026-10-20-s1-normal-multiturn.md) |
| S2 trust control | `s2/run-20261020T040447Z` | [evidence](../evidences/2026-10-20-s2-trust-control-and-interactive.md) |
| S2 interactive trust | `s2/run-20261020T040510Z` | same doc as S2 control |
| S3 permission lane | `s3/run-20261020T043111Z` | [evidence](../evidences/2026-10-20-s3-permission-lane.md) |
| S4 compaction | `s4/run-20261020T041644Z` | [evidence](../evidences/2026-10-20-s4-compaction.md) |
| S5 Esc interrupt | `s5/run-20261020T041843Z` | [evidence](../evidences/2026-10-20-s5-esc-interrupt.md) |
| S6 queue/steer | `s6/run-20261020T041916Z` | [evidence](../evidences/2026-10-20-s6-queue-steer.md) |
| S7 resume | `s7/run-20261020T042433Z` | [evidence](../evidences/2026-10-20-s7-resume.md) |
| F1 kill fault | `f1/run-20261020T042538Z` | [evidence](../evidences/2026-10-20-f1-kill-fault.md) |
| T1 pre-trusted hash | `t1/run-20261020T040411Z` | [evidence](../evidences/2026-10-20-t1-pretrusted-hash.md) |
| T2 session flags | `t2/run-20261020T040614Z` | [evidence](../evidences/2026-10-20-t2-session-flags.md) |

Flawed/superseded runs retained: `s0/run-20261020T034822Z` (gate misfire, pre-prompt SessionStart assumption), `s0/run-20261020T035053Z` (gac 402, still trust-path evidence), `t1/run-20261020T040030Z` (driver surface-timing bug), `s3/run-20261020T042923Z` (relative launcher path).

### Headline Findings per KQ

- KQ-1: auto-trust works with zero user action via two independent variants (bypass flag; pre-written `trusted_hash` — 12/12 byte-identical to Codex's own trust write). No-trust failure mode is a blocking modal that hangs unattended sessions. `-c` session-flags injection works at raw-launch level.
- KQ-2: 10 of 14 events live at 0.163.0; `PreModelRequest`/`PostModelRequest` refuted (never dispatched, excluded from trust review); subagent events unexercised; `turn_id` correlation confirmed with steer/compaction/resume semantics recorded.
- KQ-3: sync + short-timeout + stdout-silent contract validated; SessionEnd on every clean exit within ~60-600 ms; hung-hook and async-loss arms named as leftovers.
- KQ-4: `PermissionRequest` precedes the modal and follows its `PreToolUse` by ~54 ms; allow settles on matching-`tool_use_id` `PostToolUse`; deny settles on `Interrupt` (deny aborts the whole turn at 0.163.0); pair-back rule is the immediately preceding `PreToolUse` in the same `turn_id`.

### Deviations from the Frozen Workload (all recorded in their evidence docs)

1. Credential lane switched from codex-gac (HTTP 402 "No active subscription" at the S0 gate) to codex-openlux-auto, verified live same-day; campaign intent updated with the dated correction.
2. SessionStart is lazy at 0.163.0 (dispatched at first turn start, not at launch); the gate was redefined to enforce it at the first frozen prompt.
3. S3 lane required `sandbox_mode = "read-only"` in addition to `approval_policy = "on-request"` (workspace-write includes `/tmp`, so the frozen `/tmp` writes would have executed silently); the deny key is Esc (option 3), not a `d` binding — the deliverable run's deny was a manual Esc, recorded in the run's notes; the driver now auto-detects.
4. S6's predeclared "queued follow-up" semantics do not exist at 0.163.0: mid-turn input is a steer (same `turn_id`, single `Stop`).

### Named Leftovers (iteration 2 candidates)

- Hung-collector fault arm (KQ-3 P3.2) and async-loss arm (P3.3).
- `apply_patch` payload shape and `Write`/`Edit` matcher-alias behavior (KQ-2 P2.3).
- `SubagentStart`/`SubagentStop` availability and payloads (KQ-2).
- Managed-launch `-c hooks.*` canonicalization is source-supported but not live-tested through `houmao-mgr` (KQ-1 P1.4 follow-up).
- Optional S8 (`codex exec`) for exec-mode hook behavior.
