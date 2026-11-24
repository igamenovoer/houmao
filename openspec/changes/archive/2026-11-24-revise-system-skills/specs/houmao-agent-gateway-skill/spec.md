# Agent Gateway Skill Delta

## ADDED Requirements

### Requirement: Gateway lifecycle guidance covers owner deployment configuration
The gateway lifecycle page SHALL show scoped `gateway attach --access-config PATH` for the execution owner's private deployment settings. It SHALL distinguish deployment configuration, retained authorization policy, and gateway plugin selection.

#### Scenario: An operator changes live deployment settings
- **WHEN** an execution owner changes the bind, advertised address, or configured signer of a live gateway
- **THEN** the skill explains the explicit detach and attach required to apply the changed deployment settings
- **AND THEN** it directs live roster and retained policy changes to `agent-access`

#### Scenario: An operator configures gateway plugins
- **WHEN** an execution owner asks which plugins the gateway hosts
- **THEN** the skill identifies `--plugins-config` as the separate configuration for selected gateway plugins
- **AND THEN** it routes native skill and MCP freshness to the instance's native-resource workflow

### Requirement: Gateway skill supports private browser entry
The gateway skill SHALL expose `web-entry` as an explicit command for issuing one private, short-lived, single-use link to a live managed Web agent from the execution owner's context.

#### Scenario: An operator requests direct entry to a live Web agent
- **WHEN** the operator selects a live managed Web agent with an attached gateway
- **THEN** the skill shows `houmao-mgr agents single --agent-id ID gateway web-entry` or the explicit name form
- **AND THEN** it explains the owner-local address requirement, one redemption, and 60-second lifetime
- **AND THEN** it treats the URL as a bearer secret and keeps it out of shared logs and ordinary reports

#### Scenario: Browser entry is governed by the active roster
- **WHEN** the selected gateway has enrolled administrators
- **THEN** the skill requires an enrolled signer authorized for `web.enter`, using the supported option or the configured owner signer
- **AND WHEN** the selected gateway has a valid initialized empty roster
- **THEN** the skill describes unsigned issuance as available through the owner-local command

## MODIFIED Requirements

### Requirement: `houmao-agent-gateway` routes by gateway-specific intent and keeps ordinary messaging on the existing skills
The packaged `houmao-agent-gateway` skill SHALL select commands by gateway-specific intent and delegate ordinary prompt and mailbox work to the appropriate messaging or mailbox skill.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The packaged `houmao-agent-gateway` skill SHALL select commands by gateway-specific intent:

- use scoped `gateway attach|detach|status` or `/houmao/agents/{agent_ref}/gateway...` for gateway lifecycle and summary state
- use scoped `gateway mail-notifier ...` or `/houmao/agents/{agent_ref}/gateway/mail-notifier` for unread-mail notifier control
- use scoped `gateway reminders list|get|create|set|remove` or `/houmao/agents/{agent_ref}/gateway/reminders...` for reminder creation, inspection, update, and cancellation
- treat reminder delivery through the supported reminder surfaces as supporting both semantic `prompt` reminders and raw `send_keys` reminders
- select a direct live gateway HTTP route when the task needs its lower-level contract and the exact current target has been established
- delegate independently signed direct requests to `agent-access` for the supported caller and target proof
- delegate versioned file operations to `agent-files`

The packaged skill SHALL delegate ordinary prompt turns, mailbox routing, ordinary mailbox work, and transport-specific mailbox work to `houmao-agent-messaging`, `houmao-process-emails-via-gateway`, or `houmao-agent-email-comms` according to the request.

The skill SHALL prefer the scoped manager or managed-agent projection when it satisfies the task. Direct gateway HTTP guidance SHALL carry the authorization, target binding, and operation constraints of the chosen endpoint.

#### Scenario: Reminders use the native gateway reminder surfaces when available
- **WHEN** the user asks to create, inspect, update, or cancel live gateway reminders
- **THEN** the skill directs the caller to the scoped manager reminders command or the matching `/houmao/agents/{agent_ref}/gateway/reminders...` projection when pair-managed authority is in use
- **AND THEN** it does not misdescribe reminders as an HTTP-only workflow when the supported higher-level reminder surfaces already exist

#### Scenario: Direct live reminder HTTP stays the lower-level contract
- **WHEN** the user asks to debug or inspect the exact live reminder HTTP contract
- **AND WHEN** supported discovery establishes the exact current gateway target
- **THEN** the skill describes the live `{gateway.base_url}/v1/reminders...` route family and its required caller proof
- **AND THEN** it keeps that direct route family positioned as the lower-level contract rather than the first-choice operator surface

#### Scenario: Ordinary prompt or mailbox work delegates away from the gateway skill
- **WHEN** the task is one normal prompt turn, one transport-neutral interrupt, or mailbox work rather than gateway lifecycle or gateway-only service control
- **THEN** the skill directs the caller to `houmao-agent-messaging` and the current mailbox skills instead of taking that work itself
- **AND THEN** it does not present the gateway skill as the primary ordinary communication surface
