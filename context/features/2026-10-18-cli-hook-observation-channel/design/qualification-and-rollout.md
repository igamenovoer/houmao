# Qualification and Rollout

## Scope

This document defines how the CLI Hook Observation Channel is qualified, what evidence is required, which gates block enablement, and how the channel is rolled out without regressing TUI-only state tracking.

The central qualification rule is TUI-only equivalence: whenever the hook channel is absent, stale, disabled, or untrusted, every existing state field and admission outcome must match the current TUI-only baseline.

## 1. Qualification Objectives

- Prove the channel installs, starts, authenticates, and stops without changing provider behavior.
- Prove hook events normalize and correlate correctly for sessions, prompts, tools, and subagents.
- Prove the merge engine applies the authority table and publishes conflicts.
- Prove the primary robustness gains: no false-ready while a hook reports activity, immediate completion on hook terminal, immediate blocked on permission request, and known failure on API error.
- Prove fallback equivalence when hooks are missing, stale, disabled, untrusted, malformed, or out of order.
- Prove the raw event store and public diagnostics do not leak secrets.
- Prove a managed Claude session remains launchable, promptable, inspectable, and stoppable in every degraded state.

## 2. Test Layers

### 2.1 Layer 1: Normalization Unit Tests

Use synthetic provider payloads for every selected event.

Coverage:

- required and optional fields;
- unknown fields ignored;
- unknown event names counted;
- malformed JSON and missing correlation fields;
- duplicate events;
- events from an older generation;
- event payload size limits;
- normalization from each Claude event to its normalized kind and hints.

### 2.2 Layer 2: Merge State-Machine Tests

Drive the merged Rx stream with ordered and reordered observation sequences under `TestScheduler` virtual time. Assert both the emitted state sequence and the final state, not only the final reducer value.

Coverage:

- prompt start, activity, stop;
- direct-input start;
- permission request and resolution;
- API failure;
- compaction;
- subagent start and stop;
- background tasks and session crons;
- terminal event with no active turn;
- terminal event for a different prompt id;
- duplicate prompt starts;
- `stop_hook_active=true`;
- stale channel transitions;
- recovery after staleness;
- generation change.

Assertions must check both the chosen posture and the emitted conflict diagnostics.

### 2.3 Layer 3: TUI-Only Equivalence Tests

Run the existing TUI-only qualification fixtures with the hook channel absent and then with a disabled channel.

Requirements:

- `tests/unit/shared_tui_tracking/test_claude_2_1_296_qualification.py` produces identical state when the hook channel is not active.
- Existing gateway admission tests produce identical decisions.
- No new required state field breaks existing serialization or snapshot tests.

### 2.4 Layer 4: Recorded Replay with Synthetic Hook Timelines

Extend the terminal-recorder evidence model with a sidecar hook stream:

```text
<recording-root>/
  manifest.json
  pane_snapshots.ndjson
  input_events.ndjson
  hook_events.ndjson        # new sidecar
  labels.json
```

For the first pass, hook events may be synthesized from labeled turn boundaries and the transcript oracle. This validates merge ordering, authority, and conflict handling without requiring live hook delivery.

Requirements:

- Replay the existing Claude campaign recordings with no hook sidecar and confirm unchanged output.
- Replay the same recordings with a synthetic hook sidecar and confirm the expected hook-driven corrections.
- Record the exact mapping from synthetic event times to sample ids in the qualification report.

### 2.5 Layer 5: Live Managed Claude Integration

Run a managed Claude session with real hook delivery.

Scenarios:

- normal prompt turn through the gateway;
- direct prompt typed into the tmux pane;
- permission request with allow;
- permission request with deny or dismissal;
- interactive Esc interrupt;
- API failure through the existing relay or fault-injection lane;
- manual compaction;
- automatic compaction;
- subagent work;
- background task started by the agent;
- session stop and relaunch.

Evidence must include:

- channel status timeline;
- normalized event timeline;
- TUI snapshot timeline;
- merged state timeline;
- admission decisions and refusal reasons;
- conflict diagnostics;
- cleanup result.

### 2.6 Layer 6: Long-Horizon and Admission Pressure

Reuse the long-horizon tracking harness to exercise:

- long visually quiet turns;
- repeated tool batches;
- queued follow-up prompts;
- draft editing during a turn;
- compaction during a long turn;
- repeated permission waits;
- channel stalls and recoveries;
- gateway prompt admission under concurrent requests.

The goal is to prove that hooks reduce false-ready and false-busy without introducing a new stuck state.

## 3. Scenario Matrix

| Scenario | Hook evidence | Expected merged behavior | Required fallback |
| --- | --- | --- | --- |
| Normal turn | `UserPromptSubmit`, tool events, `Stop` | Active immediately, completed on `Stop`, TUI surface preserved | TUI-only if channel absent |
| Direct TUI input | `UserPromptSubmit`, `Stop` | Turn reconstructed without a gateway submission | TUI-only if channel absent |
| Visually quiet busy turn | Activity hooks present, TUI ready-looking | `turn.phase=active`, `ready_only` admission closed | TUI active evidence if channel absent |
| Permission wait | `PermissionRequest` | `waiting_user_answer`, conditional admission closed | TUI modal detection |
| Permission resolution | `PostToolUse` or `PostToolUseFailure` | Blocked cleared, turn continues | TUI modal dismissal |
| API failure | `StopFailure` | `last_turn.result=known_failure`, error class recorded | TUI error-surface handling |
| Interrupt | No hook expected | TUI `interrupted` outcome preserved | TUI temporal detector |
| Compaction | `PreCompact`, `PostCompact` | Maintenance posture, previous outcome preserved | TUI maintenance handling |
| Subagent work | `SubagentStart`, `SubagentStop` | Active count, parent turn remains active | TUI activity evidence |
| Background task | `Stop.background_tasks` | Completed turn plus `background_work_pending` | No TUI equivalent; omit flag |
| Hook channel disabled | No events | TUI-only state, `disabled_by_policy` | TUI-only baseline |
| Untrusted workspace | No events | TUI-only state, `untrusted_workspace` | TUI-only baseline |
| Collector down | Command fallback writes store | Channel may be `error`, state continues | TUI-only if store also fails |
| Stale channel | No events while TUI changes | TUI regains authority, `stale` diagnostic | TUI-only baseline |
| Malformed event | Invalid payload | Event skipped and counted, no posture change | TUI-only for that observation |
| Out-of-order async event | Late tool event | Idempotent update, no terminal reversal | TUI-only for unresolved facts |
| Duplicate stop | Two `Stop` events | One terminal result, second ignored | TUI-only baseline |
| Relaunch | New generation | Old events ignored, new turn state clean | TUI-only baseline |

## 4. Evidence Contract

Each qualification run retains a run directory with:

```text
<run-root>/
  manifest.json                 # run id, provider, version, launch posture, feature flags
  channel-status.ndjson         # channel state transitions
  hook-events.ndjson            # normalized observations, raw payloads removed or hashed
  tui-snapshots.ndjson          # existing recorder snapshots
  merged-state.ndjson           # public state after merge
  admission-decisions.ndjson    # policy, decision, refusal reasons, merged facts
  conflicts.ndjson              # conflict kind, authority, evidence timestamps
  cleanup.json                  # collector stop and artifact disposition
  report.md                     # human-readable summary and verdict
```

Rules:

- Raw provider payloads stay in the session-scoped store and are not copied into the qualification report.
- The report records payload hashes, event names, sizes, and normalized fields, not prompts or tool inputs.
- The report must state whether the run used real hooks, synthetic hooks, or both.
- The report must state the provider version and the capability set observed.
- A run with zero hook events must be labeled TUI-only, not passed as hook evidence.

## 5. Gates

Gates are ordered from cheap to expensive. A later gate does not excuse a failed earlier gate.

### G1: Schema and Serialization

- New observation and channel models serialize and deserialize.
- Existing public state snapshots remain valid with the new optional fields absent.
- Unknown event payloads do not raise.

### G2: Merge State Machine

- All normalization and merge unit tests pass.
- The Rx stream produces the expected state sequence under `TestScheduler` virtual time.
- Conflict rules produce the expected authority and diagnostics.
- Duplicate, orphan, stale, generation-mismatch, and late-TUI-snapshot cases pass.

### G3: TUI-Only Equivalence

- Existing TUI tracking and admission suites pass unchanged.
- Claude 2.1.296 qualification replay is identical with the hook channel inactive.
- No new required field or changed default appears in existing payloads.

### G4: Recorded Replay

- Frozen Claude recordings replay identically without a hook sidecar.
- The same recordings with a synthetic hook sidecar produce the expected hook-driven corrections.
- The report maps every synthetic event to a sample id and states the synthesis method.

### G5: Live Provider Smoke

- A managed Claude session starts with an active channel.
- Normal turn, direct input, permission wait, and session stop complete.
- Channel health, conflict diagnostics, and cleanup evidence are present.
- The agent remains controllable in every scenario.

### G6: Failure and Policy Matrix

- Untrusted workspace, disabled hooks, blocked HTTP URLs, collector crash, store write failure, malformed events, and stale channel are exercised.
- Each produces the expected channel state and TUI-only equivalence.
- No scenario leaves an orphan collector or an unstartable agent.

### G7: Long-Horizon Qualification

- Long visually quiet turns do not produce false-ready admission.
- Repeated permission waits do not latch blocked state after resolution.
- Compaction does not erase terminal outcomes.
- Channel stalls and recoveries do not create duplicate turns.

### G8: Release Qualification

- All prior gates pass on the maintained Claude version and the support floor.
- The TUI-only baseline remains green.
- Documentation, CLI help, and public state references are updated.
- Rollout and rollback controls are verified.

## 6. Fault Injection

Use deterministic fault injection around the collector and merge layer.

| Fault | Injection point | Expected result |
| --- | --- | --- |
| Collector never starts | Launch collector | Channel `error` or `unavailable`; TUI-only; agent runs |
| Collector dies mid-turn | Kill collector | Command fallback writes store; channel `error`; TUI continues |
| Event store read-only | File permissions | Channel `error`; TUI-only; bounded log |
| Malformed payload | Collector or test harness | Event skipped; malformed count increments |
| Unknown event | Test harness | Event ignored; unknown count increments |
| Duplicate terminal | Test harness | First terminal wins; second ignored |
| Out-of-order terminal | Test harness | Correlation by prompt id; no wrong turn completion |
| Stale generation | Test harness | Event ignored; generation mismatch counted |
| HTTP blocked | Settings policy | Command fallback or channel `error`; TUI-only |
| Workspace untrusted | Launch fixture | Channel `untrusted_workspace`; TUI-only |
| Hooks disabled | Provider policy | Channel `disabled_by_policy`; TUI-only |
| Provider version below floor | Launch fixture | Channel unsupported; session launch behavior unchanged |

## 7. Rollout

### Phase 0: Internal Opt-In

- Channel disabled by default.
- Enabled by a maintainer-only environment flag or an internal launch-profile field.
- Used to collect live evidence and refine thresholds.
- No public CLI documentation beyond the design and development docs.

### Phase 1: Managed Claude TUI Default-On

- Enabled by default for managed Claude `local_interactive` launches after G1 through G7 pass.
- Public state exposes channel health and conflict diagnostics.
- TUI-only fallback remains the default when any precondition fails.
- Headless and joined sessions remain out of scope.

### Phase 2: Headless and Additional Providers

- Evaluate `claude_headless` hooks or `--include-hook-events`.
- Add Codex and Kimi adapters against the same normalized model.
- Reuse the merge contract and qualification layers.

### Phase 3: Policy and UX Refinement

- Decide whether hook-derived final text becomes public.
- Add launch-profile controls for channel enablement and retention.
- Add operator-facing diagnostics for the top failure reasons.

## 8. Rollback

- A global environment flag or launch-profile field disables the channel for new launches.
- Existing sessions continue with their installed observer until stopped; a relaunch without the flag removes or ignores the channel.
- The tracker treats a stopped or removed channel as `unavailable` and returns to TUI-only behavior.
- No manifest migration is required because channel metadata is additive and secret-free.

## 9. Documentation Requirements

- Update TUI tracking state-model docs with the new channel status and authority table.
- Update gateway prompt-admission docs with hook refusal reasons and fallback behavior.
- Update managed-agent state references with the new optional fields.
- Update Claude provider support docs with the hook version matrix and trust preconditions.
- Add a development guide for adding a new provider adapter.
- Add a troubleshooting section for channel states and conflict diagnostics.

## Open Questions

- Should Phase 1 be gated on a minimum number of live captured turns per scenario, or on a fixed calendar window?
- Which live API-failure classes can be produced deterministically through the existing relay lane?
- Should synthetic hook sidecars be committed as fixtures, or generated at test time from labels?
- What staleness threshold should be used for admission decisions versus diagnostics?
- Should the channel be enabled for new sessions only, or also retrofitted to running sessions through the gateway?
- Should the raw event store be retained for failed sessions by default to support diagnosis?
