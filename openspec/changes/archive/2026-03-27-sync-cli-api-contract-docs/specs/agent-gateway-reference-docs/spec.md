## MODIFIED Requirements

### Requirement: Gateway operational documentation covers lifecycle and operator-facing workflows

The agent gateway operational documentation SHALL explain how to work with the gateway safely in the implemented v1 flow, including the current managed-agent operator surfaces and the strict current-session attach discovery model.

At minimum, that operational guidance SHALL cover:

- launch-time auto-attach and attach-later behavior,
- attach targeting through explicit selectors and current-session resolution,
- current-session discovery through `AGENTSYS_MANIFEST_PATH` with `AGENTSYS_AGENT_ID` plus fresh shared-registry fallback,
- the pair-managed registration precondition for current-session attach,
- detach behavior and stop-session interaction,
- status inspection and the difference between offline, unavailable, and live states,
- stale live-binding invalidation or cleanup behavior where relevant to operator workflows,
- operator-facing gateway command families for prompt, interrupt, send-keys, TUI inspection, and mail-notifier control,
- `gateway/run/current-instance.json` as the authoritative same-session live execution record when the gateway is hosted in an auxiliary tmux window.

#### Scenario: Current-session attach guidance reflects strict manifest-first discovery

- **WHEN** a reader needs to use current-session gateway attach
- **THEN** the gateway operations pages explain that attach resolves through `AGENTSYS_MANIFEST_PATH` first and `AGENTSYS_AGENT_ID` plus fresh shared-registry `runtime.manifest_path` second
- **AND THEN** the pages explain that current-session pair attach remains unavailable until the matching managed-agent registration exists on the persisted pair authority

#### Scenario: Operator can distinguish gateway command families safely

- **WHEN** a reader needs to choose between gateway prompt, raw send-keys, TUI inspection, or mail-notifier control
- **THEN** the gateway operations pages explain the purpose and boundary of each operator-facing surface
- **AND THEN** the pages do not imply that non-zero tmux windows can be rediscovered heuristically instead of following the recorded `current-instance.json` handle
