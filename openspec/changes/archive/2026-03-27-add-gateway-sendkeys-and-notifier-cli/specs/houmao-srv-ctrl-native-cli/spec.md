## MODIFIED Requirements

### Requirement: `houmao-mgr agents gateway` exposes gateway lifecycle and gateway-mediated request commands
`houmao-mgr` SHALL expose a native `agents gateway ...` command family for managed-agent gateway operations.

At minimum, that family SHALL include:

- `attach`
- `detach`
- `status`
- `prompt`
- `interrupt`
- `send-keys`
- `mail-notifier status`
- `mail-notifier enable`
- `mail-notifier disable`

`agents gateway prompt` and `agents gateway interrupt` SHALL target the managed agent's live gateway-mediated request path rather than the transport-neutral managed-agent request path.
`agents gateway send-keys` SHALL target the managed agent's dedicated live gateway raw control-input path rather than the queued gateway request path.
`agents gateway mail-notifier ...` SHALL target the managed agent's live gateway mail-notifier control path rather than the foreground managed-agent mail follow-up path.
The documented default prompt path for ordinary pair-native prompt submission SHALL remain `houmao-mgr agents prompt ...`. `agents gateway prompt` SHALL be documented as the explicit gateway-mediated path for operators who want live gateway admission and queue semantics.

#### Scenario: Operator attaches a gateway through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway attach --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed agent through the supported authority for that target
- **AND THEN** the command attaches or reuses the live gateway for that managed agent

#### Scenario: Operator submits a gateway-mediated prompt through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway prompt --agent-id abc123 --prompt "..."`
- **THEN** `houmao-mgr` delivers that request through the managed agent's live gateway-mediated request path
- **AND THEN** the command does not require the operator to discover or address the gateway listener endpoint directly

#### Scenario: Operator submits raw control input through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway send-keys --agent-id abc123 --sequence "/model<[Enter]>"`
- **THEN** `houmao-mgr` delivers that request through the managed agent's dedicated live gateway raw control-input path
- **AND THEN** the command does not reinterpret that raw control input as a queued semantic prompt request

#### Scenario: Operator enables mail notifier through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier enable --agent-id abc123 --interval-seconds 60`
- **THEN** `houmao-mgr` delivers that request through the managed agent's live gateway mail-notifier control path
- **AND THEN** the command does not require the operator to discover or address the gateway listener endpoint directly

#### Scenario: Ordinary prompt guidance points operators to the transport-neutral path by default
- **WHEN** repo-owned help text or docs explain how to submit an ordinary prompt through the native pair CLI
- **THEN** they present `houmao-mgr agents prompt ...` as the default documented path
- **AND THEN** they present `houmao-mgr agents gateway prompt ...` as the explicit gateway-managed alternative rather than the default

## ADDED Requirements

### Requirement: `houmao-mgr agents gateway` supports current-session targeting for same-session tmux operation
Gateway-targeting `houmao-mgr agents gateway ...` commands that operate on one managed agent SHALL support both explicit identity selectors and same-session current-session targeting.

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

When an operator omits explicit selectors and runs one of those commands inside the owning tmux session, `houmao-mgr` SHALL resolve the target through manifest-first current-session discovery using `AGENTSYS_MANIFEST_PATH` or `AGENTSYS_AGENT_ID`, and local resumed-control paths SHALL additionally recover `agent_def_dir` through `AGENTSYS_AGENT_DEF_DIR` or shared-registry runtime metadata.

When a command supports current-session targeting, `houmao-mgr` MAY also expose an explicit `--current-session` switch, but it SHALL treat omitted selectors inside tmux as the same current-session targeting mode.

When an operator runs one of those commands outside tmux without explicit selectors, the command SHALL fail explicitly rather than guessing from cwd, gateway listener bindings, or ambient shell state.

#### Scenario: Same-session send-keys resolves from tmux discovery without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents gateway send-keys --sequence "<[Escape]>"` from inside the owning managed tmux session
- **AND WHEN** that tmux session publishes valid manifest-first discovery metadata
- **THEN** `houmao-mgr` resolves the current managed session through that tmux-local discovery contract
- **AND THEN** it sends the control-input request without requiring `--agent-id` or `--agent-name`

#### Scenario: Same-session notifier enable resolves from tmux discovery without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier enable --interval-seconds 60` from inside the owning managed tmux session
- **AND WHEN** that tmux session publishes valid manifest-first discovery metadata
- **THEN** `houmao-mgr` resolves the current managed session through that tmux-local discovery contract
- **AND THEN** it enables notifier behavior without requiring `--agent-id` or `--agent-name`

#### Scenario: Outside-tmux gateway control fails without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents gateway send-keys --sequence "<[Escape]>"` outside tmux
- **AND WHEN** the command is not given `--agent-id`, `--agent-name`, or `--current-session`
- **THEN** the command fails explicitly
- **AND THEN** it does not guess a managed-agent target from cwd or ambient shell state

### Requirement: Server-backed gateway raw control and notifier commands accept passive server pair authorities
`houmao-mgr` server-backed `agents gateway send-keys` and `agents gateway mail-notifier ...` command paths SHALL accept `houmao-passive-server` as a supported pair authority whenever those commands operate through an explicit pair authority instead of a resumed local controller.

For these commands, `houmao-mgr` SHALL resolve the pair client through the supported pair-authority factory and SHALL use the passive server's managed-agent gateway proxy routes rather than requiring direct listener discovery from the caller.

#### Scenario: Gateway raw control input works through a passive server
- **WHEN** an operator runs `houmao-mgr agents gateway send-keys --agent-id abc123 --port 9891 --sequence "<[Escape]>"`
- **AND WHEN** the addressed pair authority identifies `houmao-passive-server`
- **THEN** `houmao-mgr` sends that raw control-input request through the passive server's managed-agent gateway proxy route
- **AND THEN** the command does not fail only because the selected pair authority is passive

#### Scenario: Gateway mail notifier control works through a passive server
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier status --agent-id abc123 --port 9891`
- **AND WHEN** the addressed pair authority identifies `houmao-passive-server`
- **THEN** `houmao-mgr` reads notifier status through the passive server's managed-agent gateway proxy route
- **AND THEN** the command does not require the operator to contact the gateway listener endpoint directly
