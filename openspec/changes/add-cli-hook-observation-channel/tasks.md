# Tasks

## 1. Floor Verification Spike

- [x] 1.1 Launch Claude Code 2.1.296 in TUI mode on this host with a generated observer `--settings` file pointing at a throwaway loopback listener, and verify `SessionStart`, `UserPromptSubmit`, and `Stop` are delivered; verify by recorded deliveries plus a findings note under `tmp/` (adjusts D5/D6 if `--settings` or HTTP hooks fail at floor)
  - Completed 2026-10-19 via campaign iteration 1: `context/campaigns/debug/2026-10-19-claude-hook-observation/evidences/2026-10-19-floor-2-1-296-s1-repeat.md` (floor verification at 2.1.296, run root `tmp/hook-capture/s1/run-20261019T141215Z/`).
- [x] 1.2 Capture real payload samples for the nine v1 events (especially `prompt_id` presence, `Stop.background_tasks`, `PermissionRequest` timing relative to the modal, `StopFailure` error fields) and verify the samples are stored under `tmp/` and the event-field mapping table is updated if reality differs from design
  - Completed 2026-10-19 via campaign iteration 1: `context/campaigns/debug/2026-10-19-claude-hook-observation/evidences/2026-10-19-hook-payload-catalog.md`; raw samples under `tmp/hook-capture/`.

## 2. Hook Observation Core Package

- [x] 2.1 Implement `src/houmao/hook_observation/` envelope model and append-only session store (`events.ndjson` mode 0600, directory 0700, generation boundary records, atomic secret-free `channel.json`) and verify unit tests cover append, generation rotation, permissions, and atomic status writes
- [x] 2.2 Implement the normalizer (v1 event set mapping to provider-neutral kinds and hints, unknown events/fields tolerated and counted, malformed payloads counted) and verify unit tests cover every v1 event plus unknown, malformed, and oversized inputs
- [x] 2.3 Implement the pure hook-posture reducer driven by `ops.scan` on an injectable scheduler (correlation by `prompt_id`, idempotent duplicates, orphan terminal handling, generation isolation, `stop_hook_active` handling) and verify `TestScheduler` unit tests cover ordered, out-of-order, duplicate, orphan, and stale-generation sequences

## 3. Collector and Emitter

- [x] 3.1 Implement the stdlib loopback collector (ephemeral port, bearer-token auth, receive-order stamping, acknowledge-before-disk, payload size cap, local health/status endpoint, secret-free `collector.json` pid record) and verify unit tests cover auth rejection, ordering, caps, and acknowledge latency
- [x] 3.2 Implement the command-hook emitter script (stdin JSON to envelope, POST to collector, append-to-store fallback, always exit 0, no stdout, bounded stderr log) and verify unit tests cover collector-up, collector-down fallback, and stdout silence
- [x] 3.3 Implement the observer settings generator (D6 event set, HTTP handlers with token env reference, command handler for `SessionStart`, secret-free output) and verify snapshot-style unit tests pin the generated settings shape and the absence of secrets

## 4. Launch Integration

- [x] 4.1 Add optional `session_root` to `LaunchPlanRequest` and make `build_launch_plan` install observer artifacts when the channel flag is on: marker-merged observer block in the managed home's `settings.json` (preserving bundle/operator entries, rewritten per launch generation, stale-block repair on reused homes) with the launch-owned `--settings` argument only as fallback for unmergeable homes, degrading to `unavailable` when neither path is safe; verify unit tests cover all paths and the flag-off no-op
- [x] 4.2 Manage collector lifecycle from `start_runtime_session`/`resume_runtime_session` (start before backend creation, new channel generation on resume/relaunch, stop at session stop) and verify integration tests cover start ordering, generation isolation, and no orphan collector after stop
- [x] 4.3 Pass the collector token to the provider through the `local_interactive` launch wrapper environment only, and verify a test asserts the token appears in the provider process environment and never in the published tmux session environment
- [x] 4.4 Plumb the opt-in enablement flag (environment variable, with launch-profile mapping if the existing profile machinery supports it cheaply) and verify tests cover enabled, disabled, and unset behavior

## 5. Tracker Merge

- [x] 5.1 Implement the session-store reader (per-consumer offset tail, unterminated-final-line retry, current-generation filter) and verify unit tests cover offsets, partial lines, and generation filtering
- [x] 5.2 Fold reader observations into `LiveSessionTracker` at `record_cycle` boundaries, reduced through the posture pipeline on the tracker's existing scheduler, and verify unit tests cover fold timing and posture availability at projection
- [x] 5.3 Apply the authority table at the existing reconciliation points: hook terminal settles `last_turn` (with `hook_observation` source, `explicit_input` preserved on correlation, `interrupted` untouched) and hook active/blocked/maintenance holds `turn.phase` against a false-ready surface, with conflict notes; verify unit tests cover each authority-table row and conflict kind
- [x] 5.4 Implement channel health (startup grace, staleness threshold, state machine transitions) and the additive public fields (`observation_channels`, diagnostics hook fields, `hook_observation` source value) and verify serialization tests cover presence, absence, and secret-freedom
- [x] 5.5 Run the TUI-only equivalence gate: `pixi run test` with the flag off, plus a byte-equivalence check that disabled-channel state equals no-channel state on the existing Claude 2.1.296 replay fixtures; verify the existing qualification and admission suites pass unchanged

## 6. Gateway and Passive Server Surfaces

- [ ] 6.1 Add hook posture gates to `ready_only` and `if_no_pending` admission (no gates when the channel is degraded, no change to `always`) and record hook facts in admission decision records and refusal details; verify unit tests cover each policy x channel-state combination
- [ ] 6.2 Add `observation_channels` to gateway status and to passive-server observation responses (local store read, `detail="remote observation"` when remote) and verify route-level tests cover both surfaces and the remote fallback

## 7. Recorded Replay and Live Qualification

- [x] 7.1 Extend the terminal-recorder evidence model with an optional `hook_events.ndjson` sidecar and make the replay path consume it; verify tests replay existing Claude fixtures unchanged without a sidecar and produce the expected hook-driven corrections with a synthesized sidecar mapped to sample ids
- [ ] 7.2 Run the live smoke campaign (managed Claude at 2.1.296 and latest: normal turn, direct pane input, permission wait, compaction, stop/relaunch, collector kill, hooks disabled, untrusted workspace) with the evidence-pack layout from the feature qualification doc under `tmp/`, and verify the campaign report records channel timelines, admission decisions, and cleanup evidence for every scenario

## 8. Documentation

- [ ] 8.1 Update the TUI tracking state-model doc with the channel status, authority table, and conflict diagnostics, and verify the documented fields match the implemented payload models
- [ ] 8.2 Update the gateway prompt-admission doc with hook gates and degraded-channel behavior, and verify the documented policies match the implemented admission checks
- [ ] 8.3 Update the Claude provider support doc with the hook version matrix, trust preconditions, and troubleshooting for channel states, and verify the documented floor matches the launch policy and detector registry pins

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
