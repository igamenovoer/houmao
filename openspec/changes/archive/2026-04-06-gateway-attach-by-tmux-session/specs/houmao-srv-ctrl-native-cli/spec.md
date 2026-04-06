## ADDED Requirements

### Requirement: `houmao-mgr agents gateway` exposes `--target-tmux-session` for explicit outside-tmux targeting
Gateway-targeting `houmao-mgr agents gateway ...` commands that operate on one managed agent SHALL accept `--target-tmux-session <tmux-session-name>` as an explicit selector in addition to the existing `--agent-id`, `--agent-name`, and same-session current-session modes.

At minimum, this SHALL apply to:

- `attach`
- `detach`
- `status`
- `prompt`
- `interrupt`
- `send-keys`
- `mail-notifier status`
- `mail-notifier enable`
- `mail-notifier disable`

For those commands, `houmao-mgr` SHALL name the explicit pair-authority override `--pair-port` rather than `--port`.

For those commands, `houmao-mgr` SHALL accept exactly one of `--agent-id`, `--agent-name`, `--target-tmux-session`, or `--current-session`, except that omitted selectors inside the owning tmux session SHALL remain equivalent to current-session targeting.

`--pair-port` SHALL remain valid only with `--agent-id` or `--agent-name`. The CLI SHALL reject `--pair-port` when the operator selects `--target-tmux-session` or `--current-session`.

The help text and error messaging for `--pair-port` SHALL describe it as the Houmao pair-authority port so operators do not confuse it with gateway listener port overrides such as lower-level `--gateway-port`.

When an operator runs one of those commands outside tmux with `--target-tmux-session`, `houmao-mgr` SHALL resolve the local managed-agent target through the addressed tmux session authority and SHALL NOT require `--agent-id` or `--agent-name`.

#### Scenario: Outside-tmux gateway status resolves by explicit tmux session selector
- **WHEN** an operator runs `houmao-mgr agents gateway status --target-tmux-session HOUMAO-gpu-coder-1-1775467167530`
- **AND WHEN** the addressed tmux session resolves to one live managed-agent target on the local host
- **THEN** `houmao-mgr` resolves that target without requiring `--agent-id` or `--agent-name`
- **AND THEN** it returns gateway status for the addressed managed session

#### Scenario: Gateway prompt supports the tmux-session selector across the command family
- **WHEN** an operator runs `houmao-mgr agents gateway prompt --target-tmux-session HOUMAO-gpu-coder-1-1775467167530 --prompt "hi"`
- **AND WHEN** the addressed tmux session resolves to one live managed-agent target on the local host
- **THEN** `houmao-mgr` submits the gateway-mediated prompt to that resolved target
- **AND THEN** the operator does not need to rediscover the managed-agent id before using the follow-up gateway command

#### Scenario: Port override is rejected for tmux-session targeting
- **WHEN** an operator runs `houmao-mgr agents gateway attach --target-tmux-session HOUMAO-gpu-coder-1-1775467167530 --pair-port 9891`
- **THEN** `houmao-mgr` rejects that invocation explicitly
- **AND THEN** the command explains that `--pair-port` is only supported with explicit `--agent-id` or `--agent-name` targeting

#### Scenario: Explicit pair-authority override uses the clearer flag name
- **WHEN** an operator runs `houmao-mgr agents gateway status --agent-id abc123 --pair-port 9891`
- **THEN** `houmao-mgr` targets the pair authority at port `9891`
- **AND THEN** the command surface does not describe that override as a generic `--port` that could be mistaken for the gateway listener port
