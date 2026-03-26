## Purpose
Define the Houmao-owned native `houmao-mgr` command tree for covered pair workflows, including server-backed managed-agent operations and local utility commands.
## Requirements
### Requirement: `houmao-mgr` exposes a native pair-operations command tree
`houmao-mgr` SHALL expose a Houmao-owned top-level native command tree.

At minimum, that native tree SHALL include:

- `server`
- `agents`
- `brains`
- `admin`

Those command families SHALL be documented as Houmao-owned pair commands.

The root group SHALL use `invoke_without_command=True` so that running `houmao-mgr` without arguments prints help text instead of raising a Python exception.

Top-level `launch` and the explicit `cao` namespace SHALL NOT remain part of the supported command tree.

#### Scenario: Native help surface shows the new top-level command families
- **WHEN** an operator runs `houmao-mgr --help`
- **THEN** the help output includes `server`, `agents`, `brains`, and `admin`
- **AND THEN** the help output does NOT include `cao` or top-level `launch`

#### Scenario: Bare invocation prints help instead of raising an exception
- **WHEN** an operator runs `houmao-mgr` without any arguments
- **THEN** the CLI prints help text showing available command groups
- **AND THEN** the CLI does NOT raise a Python exception or print a stack trace

### Requirement: `houmao-mgr server` accepts passive server pair authorities
`houmao-mgr server` lifecycle commands SHALL accept a supported pair authority whose `GET /health` reports `houmao_service == "houmao-passive-server"` in addition to `houmao-server`.

At minimum, this SHALL apply to status-style inspection and shutdown-style control commands that operate through the pair authority.

#### Scenario: Server status works against a passive server
- **WHEN** an operator runs `houmao-mgr server status --port 9891`
- **AND WHEN** the addressed server's `GET /health` response identifies `houmao-passive-server`
- **THEN** `houmao-mgr` returns lifecycle status instead of rejecting the server as unsupported

#### Scenario: Server stop works against a passive server
- **WHEN** an operator runs `houmao-mgr server stop --port 9891`
- **AND WHEN** the addressed server's `GET /health` response identifies `houmao-passive-server`
- **THEN** `houmao-mgr` calls the passive-server shutdown contract successfully
- **AND THEN** the command does not require the operator to switch back to the old server CLI

### Requirement: `houmao-mgr agents` is the preferred pair-native managed-agent command family
`houmao-mgr agents ...` SHALL be the preferred pair-native command family for managed-agent operations.

At minimum, the `agents` family SHALL include commands for:

- `launch`
- `list`
- `show`
- `state`
- `prompt`
- `interrupt`
- `relaunch`
- `stop`

Those commands SHALL target managed-agent identities rather than raw `terminal_id` or raw CAO session names as their normative addressing model.
Within that family, `show` SHALL present the detail-oriented managed-agent view, while `state` SHALL present the operational summary view.
The native `agents` family SHALL NOT advertise or require a generic `history` command as part of its supported managed-agent inspection contract.

#### Scenario: Operator inspects managed-agent state through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed-agent identity through registry-first discovery or the supported pair authority
- **AND THEN** the command returns the managed-agent state without requiring the operator to switch to raw CAO session or terminal identities

#### Scenario: Operator inspects managed-agent detail through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents show --agent-id abc123`
- **THEN** `houmao-mgr` returns the detail-oriented managed-agent view
- **AND THEN** the command does not collapse to an identity-only payload when a managed-agent detail view exists

#### Scenario: Operator submits a prompt through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id abc123 --prompt "..." `
- **THEN** `houmao-mgr` submits that request through registry-first discovery or the pair-managed agent control authority
- **AND THEN** the command does not require the operator to know whether the agent is server-backed or locally-backed

#### Scenario: Operator relaunches a managed tmux-backed session through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed-agent identity through registry-first discovery or tmux-local current-session authority
- **AND THEN** the command relaunches the existing tmux-backed managed session rather than constructing a new launch

#### Scenario: Help output does not advertise a retired history command
- **WHEN** an operator runs `houmao-mgr agents --help`
- **THEN** the help output does not list `history`
- **AND THEN** supported inspection guidance points operators to `state`, `show`, or `agents turn ...` rather than a generic managed-agent history command

### Requirement: `houmao-mgr agents gateway` exposes gateway lifecycle and gateway-mediated request commands
`houmao-mgr` SHALL expose a native `agents gateway ...` command family for managed-agent gateway operations.

At minimum, that family SHALL include:

- `attach`
- `detach`
- `status`
- `prompt`
- `interrupt`

`agents gateway prompt` and `agents gateway interrupt` SHALL target the managed agent's live gateway-mediated request path rather than the transport-neutral managed-agent request path.
The documented default prompt path for ordinary pair-native prompt submission SHALL remain `houmao-mgr agents prompt ...`. `agents gateway prompt` SHALL be documented as the explicit gateway-mediated path for operators who want live gateway admission and queue semantics.

#### Scenario: Operator attaches a gateway through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway attach <agent-ref>`
- **THEN** `houmao-mgr` resolves that managed agent through the supported pair authority
- **AND THEN** the command attaches or reuses the live gateway for that managed agent

#### Scenario: Operator submits a gateway-mediated prompt through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway prompt <agent-ref> --prompt "..." `
- **THEN** `houmao-mgr` delivers that request through the managed agent's live gateway-mediated request path
- **AND THEN** the command does not require the operator to discover or address the gateway listener endpoint directly

#### Scenario: Ordinary prompt guidance points operators to the transport-neutral path by default
- **WHEN** repo-owned help text or docs explain how to submit an ordinary prompt through the native pair CLI
- **THEN** they present `houmao-mgr agents prompt ...` as the default documented path
- **AND THEN** they present `houmao-mgr agents gateway prompt ...` as the explicit gateway-managed alternative rather than the default

### Requirement: `houmao-mgr agents gateway attach` and `detach` preserve same-host passive-server support
When an operator targets a passive server for `houmao-mgr agents gateway attach` or `houmao-mgr agents gateway detach`, the CLI SHALL prefer local registry/controller authority for those operations instead of blindly calling the passive server's HTTP attach/detach routes.

If the target cannot be resolved to a local registry-backed authority on the current host, the CLI SHALL fail explicitly that passive-server gateway attach/detach is not available through remote pair HTTP control.

#### Scenario: Gateway attach succeeds through local authority while targeting a passive server
- **WHEN** an operator runs `houmao-mgr agents gateway attach --agent-id abc123 --port 9891`
- **AND WHEN** `abc123` can be resolved to a local registry/controller authority on the current host
- **THEN** `houmao-mgr` attaches or reuses the live gateway through that local authority
- **AND THEN** the command does not fail with the passive server's HTTP 501 guidance

#### Scenario: Gateway detach fails clearly when only remote passive authority is available
- **WHEN** an operator runs `houmao-mgr agents gateway detach --agent-id abc123 --port 9891`
- **AND WHEN** `abc123` cannot be resolved to a local registry/controller authority on the current host
- **THEN** `houmao-mgr` fails explicitly that passive-server gateway detach requires local authority on the owning host
- **AND THEN** the command does not falsely claim that remote passive-server HTTP detach succeeded

### Requirement: `houmao-mgr agents mail` exposes pair-native mailbox follow-up commands
`houmao-mgr` SHALL expose a native `agents mail ...` command family for pair-managed mailbox follow-up on managed agents.

At minimum, that family SHALL include:

- `status`
- `check`
- `send`
- `reply`

Those commands SHALL address managed agents by managed-agent reference and SHALL use pair-owned mail authority rather than requiring direct gateway endpoint discovery from the caller.

#### Scenario: Operator inspects mail status through the native `agents mail` tree
- **WHEN** an operator runs `houmao-mgr agents mail status <agent-ref>`
- **THEN** `houmao-mgr` resolves that managed agent through the supported pair authority
- **AND THEN** the command returns pair-owned mailbox status without requiring the operator to reach the gateway port directly

#### Scenario: Operator checks mail through the native `agents mail` tree
- **WHEN** an operator runs `houmao-mgr agents mail check <agent-ref>`
- **THEN** `houmao-mgr` resolves that managed agent through the supported pair authority
- **AND THEN** the command returns pair-owned mailbox follow-up results without requiring the operator to reach the gateway port directly

#### Scenario: Mail command fails clearly when pair-owned mail follow-up is unavailable
- **WHEN** an operator runs `houmao-mgr agents mail send <agent-ref> ...`
- **AND WHEN** the addressed managed agent does not expose pair-owned mail follow-up capability
- **THEN** the command fails with explicit availability guidance
- **AND THEN** it does not silently claim that the mailbox action succeeded

### Requirement: `houmao-mgr agents turn` exposes managed headless turn commands
`houmao-mgr` SHALL expose a native `agents turn ...` command family for managed headless turn submission and inspection.

At minimum, that family SHALL include:

- `submit`
- `status`
- `events`
- `stdout`
- `stderr`

Those commands SHALL use the managed headless turn routes exposed by the supported pair authority.

#### Scenario: Operator submits a managed headless turn through the native `agents turn` tree
- **WHEN** an operator runs `houmao-mgr agents turn submit <agent-ref> --prompt "..." `
- **THEN** `houmao-mgr` submits that prompt through the managed headless turn authority
- **AND THEN** the command returns the accepted turn identity needed for later inspection

#### Scenario: TUI-backed agent rejects native headless turn submission
- **WHEN** an operator runs `houmao-mgr agents turn submit <agent-ref> --prompt "..." `
- **AND WHEN** the addressed managed agent is TUI-backed
- **THEN** the command fails explicitly
- **AND THEN** it does not pretend that the TUI-backed agent supports the headless turn contract

### Requirement: Server-backed managed-agent commands accept passive server pair authorities
`houmao-mgr` server-backed managed-agent command paths SHALL accept `houmao-passive-server` as a supported pair authority and SHALL resolve their managed client through the pair-authority factory.

This SHALL cover the `agents`, `agents mail`, and `agents turn` families whenever those commands are operating through an explicit pair authority instead of a resumed local controller.

#### Scenario: Managed-agent summary inspection works through a passive server
- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123 --port 9891`
- **AND WHEN** the addressed pair authority identifies `houmao-passive-server`
- **THEN** `houmao-mgr` returns the managed-agent summary view for `abc123`
- **AND THEN** the command does not fail only because the selected pair authority is passive

#### Scenario: Managed-agent detail inspection works for passive-server-managed headless agents
- **WHEN** an operator runs `houmao-mgr agents show --agent-id abc123 --port 9891`
- **AND WHEN** `abc123` is a headless agent managed by the passive server
- **THEN** `houmao-mgr` returns the managed headless detail view
- **AND THEN** the command does not require the operator to know a turn id first

#### Scenario: Headless turn submission works through a passive server
- **WHEN** an operator runs `houmao-mgr agents turn submit --agent-id abc123 --port 9891 --prompt "..." `
- **AND WHEN** the addressed pair authority identifies `houmao-passive-server`
- **THEN** `houmao-mgr` submits the turn through the passive server
- **AND THEN** the command returns the accepted turn identity needed for later inspection

### Requirement: `houmao-mgr brains build` exposes local brain construction
`houmao-mgr` SHALL expose a native `brains build` command for local brain construction.

`brains build` SHALL remain a local artifact-building command rather than a `houmao-server` API operation.

At minimum, that command SHALL support the local build inputs and outputs needed to construct a brain home and return its manifest and launch-helper pointers.

#### Scenario: Operator builds a brain without requiring `houmao-server`
- **WHEN** an operator runs `houmao-mgr brains build ...`
- **THEN** `houmao-mgr` materializes the requested local brain artifacts on the local host
- **AND THEN** the command does not require a running `houmao-server` instance just to build those artifacts

### Requirement: `houmao-mgr admin cleanup-registry` exposes local shared-registry cleanup
`houmao-mgr` SHALL expose a native `admin cleanup-registry` command for stale shared-registry cleanup.

That command SHALL remain a local maintenance operation over local runtime-owned registry state.

#### Scenario: Operator runs local shared-registry cleanup through the native admin tree
- **WHEN** an operator runs `houmao-mgr admin cleanup-registry`
- **THEN** `houmao-mgr` performs stale shared-registry cleanup on the local host
- **AND THEN** the command does not require a new `houmao-server` admin endpoint to complete that maintenance

### Requirement: Native `houmao-mgr` expansion retires `cao` namespace and top-level `launch`
Expanding `houmao-mgr` SHALL retire the `cao` command group and the top-level `launch` command entirely.

- `houmao-mgr cao *` commands SHALL be removed from the supported command tree.
- Top-level `houmao-mgr launch` SHALL be removed. Agent launch moves to `houmao-mgr agents launch`.
- The `server` group replaces server-lifecycle commands previously under `cao` (info, shutdown).
- The `agents launch` command replaces `cao launch` and top-level `launch`.

Repo-owned docs, tests, examples, and scripts SHALL use `houmao-mgr agents launch` and `houmao-mgr server *` rather than `cao launch` or top-level `launch`.

#### Scenario: `cao` namespace is no longer available
- **WHEN** an operator runs `houmao-mgr cao launch --agents ...`
- **THEN** the command fails because `cao` is not a recognized command group
- **AND THEN** help text does not list `cao` as an option

#### Scenario: Top-level launch is no longer available
- **WHEN** an operator runs `houmao-mgr launch --agents ...`
- **THEN** the command fails because `launch` is not a recognized top-level command
- **AND THEN** the operator is directed to use `houmao-mgr agents launch` instead

#### Scenario: Repo-owned scripts use the new command paths
- **WHEN** repo-owned scripts, tests, or docs reference agent launch
- **THEN** they use `houmao-mgr agents launch` rather than `houmao-mgr cao launch` or `houmao-mgr launch`

### Requirement: Repo-owned docs prefer `houmao-mgr` over `houmao-cli` for covered pair workflows
Repo-owned active documentation under `docs/` SHALL present `houmao-mgr` and `houmao-server` as the supported operator surfaces for current managed-agent and pair workflows.

References to `houmao-cli` MAY remain only in explicit migration, legacy, retirement, or historical contexts. Active documentation SHALL NOT retain `houmao-cli` as the default example for uncovered current workflows just because a native replacement has not been implemented yet.

Repo-owned documentation for managed-agent inspection SHALL NOT present `houmao-mgr agents history` as a supported native inspection surface.

#### Scenario: Active docs replace `houmao-cli` examples for supported workflows
- **WHEN** a repo-owned document under `docs/` describes a current managed-agent or pair workflow that is supported by `houmao-mgr` or `houmao-server`
- **THEN** that document uses `houmao-mgr` or `houmao-server` as the primary command example
- **AND THEN** it does not keep `houmao-cli` as the default example for that workflow

#### Scenario: Legacy `houmao-cli` references are explicitly marked as legacy
- **WHEN** a repo-owned document under `docs/` still mentions `houmao-cli`
- **THEN** that mention appears only in explicit migration, legacy, retirement, or historical guidance
- **AND THEN** it is not presented as an active default operator path

#### Scenario: Docs do not present retired managed-agent history as a supported native path
- **WHEN** repo-owned docs under `docs/` explain managed-agent inspection or long-running local/serverless operation
- **THEN** they use supported surfaces such as `houmao-mgr agents state`, `houmao-mgr agents show`, gateway TUI state, or `houmao-mgr agents turn ...`
- **AND THEN** they do not present `houmao-mgr agents history` as a supported native inspection command

### Requirement: `houmao-mgr agents relaunch` exposes tmux-backed managed-session recovery
`houmao-mgr` SHALL expose `agents relaunch` as the native managed-session recovery command for tmux-backed managed agents.

`agents relaunch` SHALL support both explicit targeting by managed-agent identity and a current-session mode when the operator runs the command from inside the owning tmux session.

The command SHALL resolve the target session through manifest-first discovery, SHALL reuse the persisted session and built home, and SHALL NOT route through build-time `houmao-mgr agents launch`.

The command SHALL fail explicitly when the target is not tmux-backed, lacks valid manifest-owned relaunch authority, or cannot be resolved through supported selector or current-session discovery.

#### Scenario: Current-session relaunch uses tmux-local discovery
- **WHEN** an operator runs `houmao-mgr agents relaunch` from inside a tmux-backed managed session
- **THEN** `houmao-mgr` resolves that session through `AGENTSYS_MANIFEST_PATH` or `AGENTSYS_AGENT_ID`
- **AND THEN** it relaunches the managed agent surface without requiring an explicit selector

#### Scenario: Explicit relaunch uses managed-agent identity
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **THEN** `houmao-mgr` resolves that live agent through registry-first discovery or the supported pair authority
- **AND THEN** it relaunches the existing tmux-backed managed session instead of creating a new launch

#### Scenario: Non-tmux-backed target fails clearly
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **AND WHEN** the resolved managed agent is not a tmux-backed relaunchable session
- **THEN** the command fails explicitly
- **AND THEN** it does not pretend that build-time launch or a raw CAO path is a supported replacement

### Requirement: Managed-agent-targeting native CLI commands use explicit identity selectors

`houmao-mgr agents` commands that target one managed agent SHALL accept explicit identity selectors instead of relying on one positional managed-agent reference.

At minimum, managed-agent-targeting commands in the `agents`, `agents gateway`, `agents mail`, and `agents turn` families SHALL accept:

- `--agent-id <id>`
- `--agent-name <name>`

For these commands, callers SHALL provide exactly one of those selectors unless the command defines a separate current-session targeting contract.

`--agent-id` SHALL target the authoritative globally unique managed-agent identity.

`--agent-name` SHALL target the friendly managed-agent name and SHALL only succeed when the relevant authority can prove that exactly one live managed agent currently uses that name.

#### Scenario: Exact selector by agent id is accepted

- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123`
- **THEN** `houmao-mgr` targets the managed agent whose authoritative identity is `abc123`
- **AND THEN** the operator does not need to rely on friendly-name uniqueness for that control action

#### Scenario: Friendly-name selector succeeds only when unique

- **WHEN** an operator runs `houmao-mgr agents show --agent-name gpu`
- **AND WHEN** exactly one live managed agent currently uses friendly name `gpu`
- **THEN** `houmao-mgr` targets that managed agent
- **AND THEN** the command succeeds without requiring the operator to spell the authoritative `agent_id`

#### Scenario: Friendly-name selector fails on ambiguity

- **WHEN** an operator runs `houmao-mgr agents prompt --agent-name gpu --prompt "..."`
- **AND WHEN** more than one live managed agent currently uses friendly name `gpu`
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error directs the operator to retry with `--agent-id`

#### Scenario: Missing selector fails when no current-session contract applies

- **WHEN** an operator runs `houmao-mgr agents stop` without `--agent-id` or `--agent-name`
- **AND WHEN** that command has no separate current-session targeting contract
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error states that exactly one of `--agent-id` or `--agent-name` is required

### Requirement: `houmao-mgr agents gateway attach` supports explicit foreground tmux-window mode for tmux-backed managed sessions
`houmao-mgr agents gateway attach` SHALL accept an explicit `--foreground` option for tmux-backed managed sessions.

When `--foreground` is requested for a runtime-owned tmux-backed managed session, `houmao-mgr` SHALL attach or reuse the gateway in same-session foreground tmux-window mode rather than detached-process mode.

When `--foreground` is requested for a pair-managed `houmao_server_rest` session that already uses same-session tmux-window gateway execution, `houmao-mgr` MAY treat that request as an explicit idempotent request for the already-supported foreground topology.

When foreground tmux-window mode is active, `houmao-mgr agents gateway attach` and `houmao-mgr agents gateway status` SHALL surface the gateway execution mode and the authoritative tmux window index for the live gateway surface so operators can inspect that console directly.

Foreground tmux-window mode SHALL NOT redefine the managed agent attach contract: tmux window `0` remains reserved for the agent surface, and the gateway window SHALL use index `>=1`.

#### Scenario: Operator requests foreground gateway attach for a runtime-owned tmux-backed session
- **WHEN** an operator runs `houmao-mgr agents gateway attach --foreground --agent-id <id>`
- **AND WHEN** the addressed managed session is a runtime-owned tmux-backed session
- **THEN** `houmao-mgr` attaches or reuses the gateway in same-session foreground tmux-window mode
- **AND THEN** the command reports the actual tmux window index for the live gateway surface

#### Scenario: Operator inspects foreground gateway status through the native CLI
- **WHEN** an operator runs `houmao-mgr agents gateway status --agent-id <id>`
- **AND WHEN** the addressed gateway is running in foreground tmux-window mode
- **THEN** the command reports `execution_mode=tmux_auxiliary_window`
- **AND THEN** the command reports the authoritative tmux window index for the live gateway surface

#### Scenario: Foreground attach preserves the agent surface contract
- **WHEN** an operator requests foreground gateway attach for a tmux-backed managed session
- **THEN** the gateway attaches in a tmux window whose index is `>=1`
- **AND THEN** tmux window `0` remains the managed agent surface
