## ADDED Requirements

### Requirement: Managed-agent summary state exposes gateway and mailbox posture and includes a detailed state route
In addition to the existing managed-agent summary state route, `houmao-server` SHALL expose `GET /houmao/agents/{agent_ref}/state/detail` for transport-specific inspection.

`GET /houmao/agents/{agent_ref}/state` SHALL remain the coarse shared state surface, and SHALL include redacted mailbox and gateway summary fields when those capabilities are known for the addressed managed agent.

The detailed route SHALL use the same managed-agent alias resolution rules as the rest of the managed-agent API.

#### Scenario: Summary state shows mailbox and gateway posture
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state` for a mailbox-enabled managed agent whose gateway capability is published
- **THEN** the returned coarse state includes redacted mailbox and gateway summary information
- **AND THEN** the caller can tell that the agent is mailbox-enabled and gateway-capable without reading manifests directly

#### Scenario: Managed-agent alias resolves to the detail route
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/state/detail` using any supported managed-agent alias
- **THEN** `houmao-server` resolves that alias through the managed-agent identity rules
- **AND THEN** the returned detail payload describes the resolved managed agent rather than requiring a transport-specific route key from the caller

### Requirement: Managed-agent control accepts transport-neutral request submission
`houmao-server` SHALL expose `POST /houmao/agents/{agent_ref}/requests` as a transport-neutral managed-agent request-submission route.

In this change, that request surface SHALL accept at minimum:

- `submit_prompt`
- `interrupt`

The request body SHALL use a typed request-kind contract rather than a transport-private prompt or terminal-input payload shape.

Accepted requests SHALL return one transport-neutral accepted-request response shape for both `submit_prompt` and `interrupt`.

That accepted response SHALL identify the accepted request and MAY include explicit no-op detail when the request required no transport mutation.

For managed headless agents, accepted prompt submission through that route SHALL be backed by the server-owned headless turn authority for that agent.

For managed TUI agents, accepted prompt submission through that route SHALL use the transport-appropriate TUI control path.

For managed headless agents, the accepted response SHALL include enough metadata to relate the accepted request to the created headless turn when a new turn was created.

This change SHALL NOT require a durable `/houmao/agents/{agent_ref}/requests/{request_id}` follow-up route.

The existing headless `/turns` route family SHALL remain the durable headless per-turn detail surface.

Request-validation failures on `POST /houmao/agents/{agent_ref}/requests` SHALL return HTTP `422`.

Admission conflicts such as an already-active headless turn or reconciliation-required execution blocking SHALL return HTTP `409`.

Managed-agent unavailable or recovery-blocked admission failures SHALL return HTTP `503`.

Interrupt requests that target a managed agent with no active interruptible work SHALL return an explicit transport-neutral no-op response rather than pretending that an interrupt was delivered.

#### Scenario: Headless prompt request returns headless turn linkage
- **WHEN** a caller submits a `submit_prompt` managed-agent request for a managed headless agent that can accept a new prompt
- **THEN** `houmao-server` accepts that request through its managed-agent request surface
- **AND THEN** the accepted response uses the transport-neutral request envelope and identifies the corresponding server-owned headless turn created for that prompt

#### Scenario: TUI prompt request uses the same managed-agent control route
- **WHEN** a caller submits a `submit_prompt` managed-agent request for a managed TUI agent
- **THEN** `houmao-server` accepts that request through the same managed-agent request route family
- **AND THEN** the caller does not need to switch to a separate transport-private route family solely to submit managed work

#### Scenario: Interrupt request remains transport-neutral
- **WHEN** a caller submits an `interrupt` managed-agent request for a managed TUI or headless agent
- **THEN** `houmao-server` accepts that request through the same managed-agent request surface
- **AND THEN** the transport-specific interrupt path remains an implementation detail rather than a caller-visible API split

#### Scenario: Busy headless prompt admission returns conflict semantics
- **WHEN** a caller submits a `submit_prompt` managed-agent request for a managed headless agent that already has one active managed turn
- **THEN** `houmao-server` rejects that admission with HTTP `409`
- **AND THEN** the request route does not silently queue or overlap a second headless turn for that agent

#### Scenario: Recovery-blocked managed agent returns unavailable semantics
- **WHEN** a caller submits a managed-agent request for an agent whose authority record exists but whose runtime cannot currently resume or admit work
- **THEN** `houmao-server` rejects that request with HTTP `503`
- **AND THEN** the response does not pretend that the request was accepted for later execution

#### Scenario: Interrupt with no active work returns explicit no-op detail
- **WHEN** a caller submits an `interrupt` managed-agent request for a managed agent with no active interruptible work
- **THEN** `houmao-server` returns the same transport-neutral accepted response family with explicit no-op detail
- **AND THEN** the caller is not forced to guess whether the interrupt request was delivered or ignored

#### Scenario: Invalid managed-agent request payload returns validation semantics
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/requests` with an invalid typed request payload
- **THEN** `houmao-server` rejects that request with HTTP `422`
- **AND THEN** the managed-agent request route does not reinterpret that invalid payload as a transport-private prompt submission

### Requirement: `houmao-server` exposes managed-agent gateway operational routes
For managed agents whose sessions are gateway-capable, `houmao-server` SHALL expose managed-agent gateway lifecycle and inspection routes.

At minimum, that route family SHALL include:

- `POST /houmao/agents/{agent_ref}/gateway/attach`
- `POST /houmao/agents/{agent_ref}/gateway/detach`
- `GET /houmao/agents/{agent_ref}/gateway`
- `GET /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `PUT /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`

Those routes SHALL operate against the same underlying gateway capability and durable gateway state used by the gateway sidecar itself.

Those routes SHALL NOT redefine the gateway mailbox facade as part of this change; direct mailbox operations remain on the gateway HTTP surface.

If a healthy live gateway is already attached for the addressed managed agent, `POST /houmao/agents/{agent_ref}/gateway/attach` SHALL behave idempotently and return the current attachment or status rather than starting a second gateway instance.

If persisted and live gateway state disagree or require reconciliation before safe reuse, `POST /houmao/agents/{agent_ref}/gateway/attach` SHALL fail explicitly with HTTP `409` rather than silently replacing the existing live gateway state.

#### Scenario: Server attaches a gateway for a managed headless agent
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/attach` for a gateway-capable managed headless agent
- **THEN** `houmao-server` attaches a live gateway for that managed agent through the official managed-agent route family
- **AND THEN** the caller does not need to resume manifests or invoke runtime-private attach logic directly

#### Scenario: Gateway status remains readable through the managed-agent API
- **WHEN** a caller requests `GET /houmao/agents/{agent_ref}/gateway` for a managed agent whose gateway is detached or not yet attached
- **THEN** `houmao-server` still returns the current gateway capability or offline status for that managed agent
- **AND THEN** the caller does not need direct filesystem access to inspect stable gateway state

#### Scenario: Gateway attach is idempotent when a healthy gateway is already attached
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/attach` for a managed agent that already has a healthy live gateway attached
- **THEN** `houmao-server` returns the current gateway attachment or status rather than starting a second gateway process
- **AND THEN** the attach route remains safe for retry-oriented automation

#### Scenario: Reconciliation-required gateway attach fails explicitly
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/attach` and the persisted gateway state indicates a stale or reconciliation-required condition
- **THEN** `houmao-server` rejects that attach request with HTTP `409`
- **AND THEN** the route does not silently detach or replace the existing gateway state

#### Scenario: Server route controls notifier without redefining the gateway mail facade
- **WHEN** a caller enables or inspects notifier behavior through `/houmao/agents/{agent_ref}/gateway/mail-notifier`
- **THEN** `houmao-server` operates on the same notifier state used by the gateway sidecar
- **AND THEN** mailbox send, check, and reply remain on the gateway HTTP surface rather than being silently redefined under the server route family

### Requirement: Native headless launch accepts official mailbox options while gateway lifecycle remains separate
`POST /houmao/agents/headless/launches` SHALL accept optional structured mailbox configuration in addition to the existing required resolved launch inputs.

Mailbox configuration MAY override or refine the effective mailbox transport and redacted mailbox identity resolved for that managed headless launch.

Gateway lifecycle for the launched managed agent SHALL remain a separate post-launch action under the managed-agent gateway route family and SHALL NOT be coupled to the headless launch request in this change.

Persisted blueprint or manifest-backed gateway defaults MAY still influence a later attach action, but those defaults are not caller-supplied launch inputs for `POST /houmao/agents/headless/launches`.

Notifier configuration SHALL remain a separate operational control action rather than a launch-time identity field.

Validation failures for invalid mailbox launch options or unexpected launch-time gateway fields SHALL return HTTP `422`.

#### Scenario: Native headless launch requests mailbox override
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` with valid required launch inputs and an optional mailbox override block
- **THEN** `houmao-server` validates and applies that mailbox configuration through the official launch contract
- **AND THEN** the launched managed headless agent exposes the resulting mailbox posture through the managed-agent state surfaces

#### Scenario: Native headless launch remains decoupled from gateway attach
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` with valid required launch inputs and later requests `POST /houmao/agents/{agent_ref}/gateway/attach`
- **THEN** `houmao-server` treats the launch and attach steps as separate managed-agent lifecycle actions
- **AND THEN** the managed agent does not need to be re-launched or reconfigured through manifest-private inputs solely to attach a gateway later

#### Scenario: Launch-time gateway fields are rejected explicitly
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` with gateway-specific launch fields that are not part of the official launch contract
- **THEN** `houmao-server` rejects that request with HTTP `422`
- **AND THEN** callers are directed to the managed-agent gateway route family for later attach or detach behavior
