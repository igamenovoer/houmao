## Context

Gateway-owned TUI tracking uses `SingleSessionTrackingRuntime`, which currently defaults to a 0.5 second poll interval, 1.0 second readiness stability window, 1.0 second completion stability window, and 30.0 second unknown-to-stalled timeout. The underlying `LiveSessionTracker` also has a 5.0 second stale-active recovery window. `houmao-server` exposes most of these timings on its server launch CLI, but the per-agent gateway path constructs its own tracking runtime with defaults and no launch-time override surface.

The gateway attach path spans CLI, pair-server API, runtime controller, gateway service subprocess launch, gateway desired configuration, and the gateway-owned tracker. The timing configuration therefore needs to travel as structured launch/attach intent instead of isolated command flags.

## Goals / Non-Goals

**Goals:**

- Expose gateway-owned TUI tracking timing controls on `houmao-mgr agents gateway attach`.
- Expose the same controls for launch-time auto-attach on `houmao-mgr project easy instance launch`.
- Allow pair-owned `POST /houmao/agents/{agent_ref}/gateway/attach` callers to supply the same timing controls.
- Persist resolved timing values in the gateway desired config so gateway restart and later attach reuse the selected tracking behavior.
- Keep existing defaults unchanged when no override is supplied.

**Non-Goals:**

- Do not change `houmao-server` background watch timing flags beyond reusing the same timing vocabulary.
- Do not expose the TUI reset-context `/clear` wait and poll constants in this change.
- Do not change Claude, Codex, or Gemini detector logic.
- Do not make gateway timing configuration part of launch-profile authoring defaults in this change.

## Decisions

1. Use one shared gateway TUI tracking timing model internally.

   The timing fields should be represented as one optional structured object with:

   - `watch_poll_interval_seconds`
   - `stability_threshold_seconds`
   - `completion_stability_seconds`
   - `unknown_to_stalled_timeout_seconds`
   - `stale_active_recovery_seconds`

   This avoids threading five unrelated optional floats through every boundary and gives CLI, API, desired config, and subprocess launch one validation vocabulary. The alternative was to add flat fields at every boundary; that is easier initially but makes precedence and validation drift more likely.

2. Resolve precedence at attach time.

   The effective timing config should resolve in this order:

   1. explicit CLI/API attach override
   2. persisted gateway desired config
   3. shared gateway tracking defaults

   This matches existing host, port, and execution-mode behavior, where explicit attach intent wins and successful attach refreshes the desired config. The alternative was process-only flags that disappear after the child starts; that would not satisfy restart or later attach reuse.

3. Use public CLI option names prefixed with `--gateway-tui-*`.

   Public `houmao-mgr` flags should be:

   - `--gateway-tui-watch-poll-interval-seconds`
   - `--gateway-tui-stability-threshold-seconds`
   - `--gateway-tui-completion-stability-seconds`
   - `--gateway-tui-unknown-to-stalled-timeout-seconds`
   - `--gateway-tui-stale-active-recovery-seconds`

   The prefix keeps them visually tied to the gateway sidecar and avoids implying that they tune the provider launch process itself. The internal gateway service CLI can use the shorter `--tui-*` names because it is only launched as the gateway process.

4. Persist timing config as additive optional desired-config fields.

   `GatewayDesiredConfigV1` should gain an optional nested timing object. Old desired-config files that omit the object should continue to read as "use defaults." New desired-config files may include explicit timing values after a successful attach. This avoids a migration-only task for existing session roots. The trade-off is that older binaries may reject new desired-config files because the model is strict; the repository is explicitly under active development, so rollback compatibility is not a goal here.

5. Validate all timing values as positive floats.

   Every exposed timing value should be `> 0`. A zero stale-active recovery window would turn the safeguard into immediate recovery and could mask legitimate active turns. A zero poll interval would create a busy loop. The alternative of allowing `0` to disable specific behaviors can be revisited later with explicit semantics.

## Risks / Trade-offs

- Older binaries may reject desired-config files containing the new timing object -> This repository does not prioritize rollback compatibility during active development; the new code should still read old files that omit the object.
- Too many public timing flags can make the easy launch help noisy -> Use a consistent `--gateway-tui-*` prefix and concise help text that distinguishes tracker timings from provider launch behavior.
- Timing values can be misconfigured to make readiness sluggish or overly aggressive -> Require positive values, keep current defaults, and surface resolved timing values through existing TUI state lifecycle metadata where available.
- Pair-server attach and local attach can diverge if they use separate request shapes -> Use the same internal timing model and add tests for both paths.
