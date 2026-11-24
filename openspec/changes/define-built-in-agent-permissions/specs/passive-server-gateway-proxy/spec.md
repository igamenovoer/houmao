# Spec Delta

## ADDED Requirements

### Requirement: Passive Proxies Preserve Work Request and Control Authority

Selected-agent gateway proxies SHALL resolve the delivery effect from the validated operation and apply the same exact permissions as the target gateway. The request proxy SHALL forward `submit_work_request` as a typed work request and preserve the admitted caller through the owner-local relay. Direct, slash, interrupt, and raw effects SHALL retain their declared permissions and current-authority checks.

#### Scenario: A requester reaches Bob through the passive server
- **WHEN** Alice signs a `submit_work_request` on Bob's passive gateway request proxy with `agent.request.submit`
- **THEN** Bob's gateway receives the typed request with Alice's verified authority
- **AND THEN** the proxy returns the original acceptance or refusal with its request identity when available

#### Scenario: A new peer uses Bob's default through the passive server
- **WHEN** a new peer sends `submit_work_request` without proof or Bob-side enrollment through Bob's passive proxy, and Bob's keyed policy defaults to `agent-requester`
- **THEN** passive ingress admits the exact request under Bob's default policy and relays anonymous provenance
- **AND THEN** the receiving gateway checks the default authority against current policy before admitting the request

#### Scenario: Relayed default authority is no longer current
- **WHEN** the passive ingress admits a work request under Bob's default but current policy withdraws that authority before gateway admission
- **THEN** the gateway refuses the relayed request before native work

#### Scenario: A proxy request submits invalid caller proof
- **WHEN** an otherwise permitted work request includes invalid proof
- **THEN** passive ingress refuses it before producing an owner-local relay

#### Scenario: A requester attempts a direct prompt through the passive server
- **WHEN** Alice presents only work-request authority for a direct prompt through the passive proxy
- **THEN** admission refuses the direct effect before owner-local relay or native work

#### Scenario: A slash command arrives through proxied direct input
- **WHEN** a signed proxy request uses direct input the selected target could interpret as a supported slash command
- **THEN** passive admission and gateway handoff check the matching command authority and any additional effects before native delivery

#### Scenario: A running target has no attached gateway for a work request
- **WHEN** Carol submits `submit_work_request` to the passive gateway proxy for running Bob while his gateway is detached
- **THEN** the proxy reports the gateway's unavailability through its existing contract without queuing the request or starting a native turn

### Requirement: Direct Passive Work Requests Preserve Requester Authority

`POST /houmao/agents/{agent_ref}/work-requests` SHALL accept only `submit_work_request` for a verified running target with a detached gateway and a qualified owner-native path. It SHALL authorize `agent.request.submit` using the retained policy and render bounded text as attributed, quoted content. It SHALL use the current conversation and configured model and require ready-only admission.

#### Scenario: Carol sends work to detached managed headless Bob
- **WHEN** Carol selects the direct passive route for ready, detached Bob and submits a valid work request under the requester default or a verified requester assignment
- **THEN** the passive server hands off the request through Bob's qualified managed headless owner path
- **AND THEN** the renderer preserves verified or anonymous provenance and quotes command-shaped content as work-request data

#### Scenario: A caller requests a direct effect in a work request
- **WHEN** a caller supplies verbatim command mode, raw input, a session or model override, or a readiness override in a direct passive work request
- **THEN** the passive server refuses the invalid payload before native work

#### Scenario: A verified observer submits wrapped work
- **WHEN** keyed Bob recognizes Carol as an observer with no additional request permission
- **THEN** the passive server refuses the request even if Bob's default would admit an eligible unsigned request

### Requirement: Direct Passive Work Requests Use Qualified Immediate Handoff

Passive ingress SHALL recheck the original authority, target generation, detached selection, and readiness at the owner-native handoff. The direct path SHALL attempt one immediate handoff. It SHALL return a bounded request reference and admission or handoff evidence when available. Private turn output SHALL require separately authorized access.

#### Scenario: The target cannot accept a ready-only handoff
- **WHEN** Bob is busy, the live body is unavailable, or the passive server has no qualified owner path
- **THEN** the direct operation reports the applicable refusal or unavailable result before native work
- **AND THEN** it leaves no queued work and starts no gateway or replacement agent

#### Scenario: The selected authority changes before native handoff
- **WHEN** Carol loses the original authority or Bob's generation or gateway attachment changes before handoff
- **THEN** the passive server settles the original attempt without a native effect or a submission to the new gateway

#### Scenario: Native handoff cannot be confirmed
- **WHEN** the direct attempt loses confirmation after work may have reached the native body
- **THEN** the passive server preserves and reports the strongest available evidence and does not claim completion or retry submission

### Requirement: Direct Passive Input Retains Its Control Authority

Direct passive prompt and headless turn endpoints SHALL require `agent.prompt.direct` and any other declared effects of their validated input. The selected agent's retained policy SHALL apply before native execution or owner handoff, including when no gateway is attached. The passive backing credential SHALL remain independently scoped.

#### Scenario: A requester targets a detached headless turn
- **WHEN** Alice has only `agent.request.submit` and submits a direct turn through the passive server for a headless Bob with no gateway
- **THEN** the retained policy refuses direct prompt authority before a provider worker starts

#### Scenario: A direct caller targets a suitable detached body
- **WHEN** Alice has direct prompt authority and any additional required effects for a supported direct passive prompt or turn
- **THEN** the passive server uses its existing direct execution and native readiness contract without requiring gateway attachment

#### Scenario: A split prompt permission expires at handoff
- **WHEN** a direct passive operation loses an admitted prompt, command, or override permission before owner handoff
- **THEN** the original operation fails before the owner applies the requested effect

### Requirement: Passive Administration Updates the Retained Default Directly

`PUT /houmao/agents/{agent_ref}/admin/default-permission-group` SHALL use the gateway setter's request and result contract. Passive ingress SHALL authorize `admin.default-group.set` on `policy` for the verified retained target and recheck current effective `agent-admin` authority at commit. The route SHALL write to the owner's retained policy without a live gateway.

#### Scenario: A passive admin updates a stopped target

- **WHEN** passive ingress admits a default-group request under effective admin authority for a stopped target with verified retained policy
- **THEN** the passive server commits the group and reports its revision without forwarding to a gateway or starting the target
- **AND THEN** the gateway and recipient mail transports use that same retained policy

#### Scenario: Passive ingress receives an unqualified request

- **WHEN** the caller lacks effective admin authority, supplies invalid proof, or the passive server cannot verify the retained owner and policy
- **THEN** the request fails before mutation
- **AND THEN** the passive server uses neither its backing credential nor another target's policy as authority

## MODIFIED Requirements

### Requirement: Direct passive paths cannot bypass protected agent access

Direct selected-agent operations SHALL apply retained policy to the exact target, resource, and action before effects. Current administrators SHALL have access to every supported client-facing operation in that domain. A valid empty roster SHALL give callers the same access. Operation-specific proof and runtime guards SHALL still apply. The passive ingress SHALL issue and verify its own challenges independently of gateway discovery.

#### Scenario: Direct stop would otherwise kill tmux

- **WHEN** an unauthenticated caller invokes direct stop for a discovered agent with a nonempty admin list and the agent's default group lacks stop authority
- **THEN** the server rejects it before tmux termination or registry cleanup

#### Scenario: Direct headless match has no discovery record

- **WHEN** a protected managed-headless target is found through its retained control state without a live discovery record
- **THEN** prompt, interrupt, stop, protected state, and artifact requests require permission for the exact resource and action

#### Scenario: Gateway detachment removes its live record

- **WHEN** a protected target has no live gateway record after detachment
- **THEN** direct protected operations still use the current retained policy for that target domain

#### Scenario: Enrollment races a direct anonymous operation

- **WHEN** a direct operation's anonymous grant has ceased to be current before its effect boundary
- **THEN** the operation is refused before accessing or changing the target
