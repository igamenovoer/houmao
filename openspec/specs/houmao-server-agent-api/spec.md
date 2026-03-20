## Purpose
Define the Houmao-owned managed-agent API for shared managed-agent discovery, transport-neutral read surfaces, and native headless lifecycle control.

## Requirements

### Requirement: `houmao-server` exposes a transport-neutral managed-agent read API
`houmao-server` SHALL expose Houmao-owned managed-agent routes in addition to the CAO-compatible core API and the existing terminal-keyed Houmao routes.

The managed-agent read surface SHALL include at minimum:

- `GET /houmao/agents`
- `GET /houmao/agents/{agent_ref}`
- `GET /houmao/agents/{agent_ref}/state`
- `GET /houmao/agents/{agent_ref}/history`

Those routes SHALL work for both TUI-backed agents and headless agents admitted into server authority.

The managed-agent identity returned by those routes SHALL include a transport discriminator plus a server-owned stable tracked-agent identity.

The managed-agent state returned by those routes SHALL use a transport-neutral contract for coarse availability and turn posture, and SHALL NOT require callers to interpret TUI-only parsed-surface fields or headless-only raw artifact files.

`GET /houmao/agents/{agent_ref}/history` SHALL expose bounded coarse recent managed-agent history across both transports rather than a durable per-turn log surface.

#### Scenario: Shared discovery lists both TUI and headless managed agents
- **WHEN** `houmao-server` is managing one TUI-backed agent and one headless Claude agent
- **THEN** `GET /houmao/agents` returns both managed agents
- **AND THEN** each returned entry identifies its transport kind without requiring a caller to infer it from route shape alone

#### Scenario: Shared state is readable without terminal scraping
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state` for a managed agent
- **THEN** `houmao-server` returns a transport-neutral coarse state payload for that agent
- **AND THEN** the caller does not need to reconstruct that coarse state by scraping raw terminal output or headless artifact files directly

#### Scenario: Shared history stays bounded and coarse
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/history` for a managed headless or TUI agent
- **THEN** `houmao-server` returns bounded coarse recent managed-agent history for that agent
- **AND THEN** the route does not redefine itself as the durable per-turn history surface

### Requirement: `houmao-server` exposes a native headless launch and stop API
For Houmao-managed headless agents, `houmao-server` SHALL expose Houmao-owned lifecycle routes that do not depend on CAO session or terminal creation.

At minimum, the native headless lifecycle surface SHALL include:

- `POST /houmao/agents/headless/launches`
- `POST /houmao/agents/{agent_ref}/stop`

`POST /houmao/agents/headless/launches` SHALL accept a resolved runtime launch request for a native headless agent.

In v1, that launch request SHALL require at minimum:

- `tool`
- `working_directory`
- `agent_def_dir`
- `brain_manifest_path`
- `role_name`

That request MAY include optional identity hints such as `agent_name` and `agent_id`.

The raw HTTP launch contract SHALL NOT rely on pair-style convenience fields such as `provider`, `agent_source`, or installed profile name as its normative launch shape.

Validation failures such as missing required resolved launch fields or conflicting launch-input combinations SHALL return HTTP `422`.

When a headless launch succeeds, `houmao-server` SHALL return the managed-agent identity plus server-owned manifest and session-root pointers for the launched headless agent.

Native headless launch SHALL NOT require or depend on creating a child-CAO session or terminal first.

`POST /houmao/agents/{agent_ref}/stop` SHALL stop a managed headless agent through the Houmao-owned headless lifecycle rather than through CAO terminal-stop semantics.

#### Scenario: Native headless launch creates a managed agent without CAO terminal identity
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` for a Claude headless agent
- **THEN** `houmao-server` launches that headless agent through a Houmao-owned headless path
- **AND THEN** the returned managed-agent identity does not require a CAO `terminal_id`

#### Scenario: Native headless launch accepts resolved runtime inputs
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` with `tool`, `working_directory`, `agent_def_dir`, `brain_manifest_path`, and `role_name`
- **THEN** `houmao-server` validates that request as a native headless launch request
- **AND THEN** a successful response returns the tracked-agent identity plus manifest and session-root pointers for the launched headless agent

#### Scenario: Convenience-only launch shape is rejected with validation semantics
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` using only convenience fields such as `provider` or `agent_source` without the required resolved runtime inputs
- **THEN** `houmao-server` rejects that request with HTTP `422`
- **AND THEN** the raw server launch contract remains native and explicit rather than convenience-shaped

#### Scenario: Native headless stop does not use terminal-stop compatibility routes
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/stop` for a managed headless agent
- **THEN** `houmao-server` stops that agent through the Houmao-owned headless lifecycle
- **AND THEN** the caller does not need to treat the headless agent as a fake CAO terminal to stop it

### Requirement: Managed-agent lookup resolves through explicit aliases
`houmao-server` SHALL resolve `/houmao/agents/{agent_ref}` lookups through a server-owned tracked-agent identity plus explicit aliases.

At minimum, supported aliases SHALL include:

- the server-owned tracked-agent id
- `terminal_id` and `session_name` for TUI-backed agents
- runtime-owned manifest-backed identity such as runtime session id when present
- `agent_id` and `agent_name` when present

When more than one managed agent matches the supplied alias, `houmao-server` SHALL reject the lookup as ambiguous rather than silently selecting one match.

#### Scenario: TUI terminal alias resolves to the shared managed-agent surface
- **WHEN** a caller looks up `/houmao/agents/{agent_ref}` using the `terminal_id` alias of a managed TUI agent
- **THEN** `houmao-server` resolves that alias to the corresponding managed-agent identity
- **AND THEN** the caller can inspect shared managed-agent state without switching to a different identity namespace first

#### Scenario: Ambiguous alias is rejected explicitly
- **WHEN** more than one managed agent matches the supplied `/houmao/agents/{agent_ref}` alias
- **THEN** `houmao-server` rejects the lookup as ambiguous
- **AND THEN** it does not silently choose one managed agent and hide the identity conflict

### Requirement: Headless prompt control is modeled as turn resources
For server-launched managed headless agents, `houmao-server` SHALL expose Houmao-owned turn-control and turn-inspection routes under `/houmao/agents/{agent_ref}`.

At minimum, the headless route surface SHALL include:

- `POST /houmao/agents/{agent_ref}/turns`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stderr`
- `POST /houmao/agents/{agent_ref}/interrupt`

`POST /houmao/agents/{agent_ref}/turns` SHALL accept one prompt submission for a headless managed agent and SHALL return a server-owned turn identity that callers can use for later status and artifact inspection.

`houmao-server` SHALL allow at most one active server-managed headless turn per managed agent at a time in v1. If a later prompt submission arrives while a previous turn is still active for that agent, the server SHALL reject the later submission explicitly.

Headless turn routes SHALL reject TUI-backed agents explicitly rather than pretending they share the same turn-execution contract.

#### Scenario: Headless prompt submission returns a turn handle
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/turns` for a server-launched managed Claude headless agent with no active turn
- **THEN** `houmao-server` accepts that prompt submission as a new headless turn
- **AND THEN** the response includes a server-owned `turn_id` that the caller can use for status and event inspection

#### Scenario: Concurrent headless turn submission is rejected
- **WHEN** a managed headless agent already has one active server-managed turn
- **AND WHEN** a caller submits another `POST /houmao/agents/{agent_ref}/turns` for that same agent
- **THEN** `houmao-server` rejects the later submission explicitly
- **AND THEN** it does not start overlapping resumed CLI turns for the same managed headless session

#### Scenario: Restart preserves active-turn conflict handling
- **WHEN** `houmao-server` restarts while a previously accepted headless turn for one managed agent remains active
- **AND WHEN** a caller submits a new `POST /houmao/agents/{agent_ref}/turns` for that same agent after restart
- **THEN** `houmao-server` continues rejecting the later submission until the recorded earlier turn reconciles to a terminal state
- **AND THEN** single-active-turn semantics remain stable across restart

#### Scenario: TUI agent rejects headless turn submission
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/turns` for a TUI-backed managed agent
- **THEN** `houmao-server` rejects that request explicitly
- **AND THEN** the caller must continue using the transport-appropriate TUI control surface instead of the headless turn API

### Requirement: Headless turn inspection exposes structured events and durable artifacts
For accepted headless turns, `houmao-server` SHALL expose both structured event inspection and raw durable artifact inspection.

`GET /houmao/agents/{agent_ref}/turns/{turn_id}` SHALL report the current or terminal status of the referenced turn using manifest and artifact-backed evidence.

`GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` SHALL expose structured event records derived from machine-readable headless turn output rather than requiring callers to parse raw `stdout.jsonl` themselves.

The artifact routes SHALL expose the durable turn artifacts for that accepted headless turn without requiring direct filesystem access from the caller.

`POST /houmao/agents/{agent_ref}/interrupt` SHALL provide best-effort interruption for the active headless turn of that agent.

#### Scenario: Caller inspects structured headless turn events
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` for an accepted headless turn
- **THEN** `houmao-server` returns structured event records derived from the machine-readable turn output
- **AND THEN** the caller does not need to read or parse `stdout.jsonl` directly from the filesystem

#### Scenario: Caller inspects durable stderr artifact
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stderr` for an accepted headless turn
- **THEN** `houmao-server` returns the durable stderr artifact for that turn
- **AND THEN** the caller does not need direct filesystem access to the headless session root to inspect it

#### Scenario: Interrupt targets the active headless turn only
- **WHEN** a managed headless agent has one active server-managed turn
- **AND WHEN** a caller submits `POST /houmao/agents/{agent_ref}/interrupt`
- **THEN** `houmao-server` delivers a best-effort interrupt to that active headless turn
- **AND THEN** the interrupt request does not fabricate interruption for already-completed turns

### Requirement: Durable headless detail stays on per-turn resources rather than shared `/history`
For managed headless agents, durable post-turn inspection SHALL live on the per-turn route family rather than on the shared `/houmao/agents/{agent_ref}/history` route.

`GET /houmao/agents/{agent_ref}/history` MAY be empty or truncated after restart even when earlier headless turns remain inspectable through their per-turn status, event, and artifact routes.

#### Scenario: Headless caller uses per-turn routes for durable inspection
- **WHEN** a caller needs durable detail for a previously completed headless turn
- **THEN** the caller can inspect that turn through `/houmao/agents/{agent_ref}/turns/{turn_id}` and its nested `events` or `artifacts` routes
- **AND THEN** the shared `/history` route does not need to duplicate that durable turn detail
