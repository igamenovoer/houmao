## ADDED Requirements

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
