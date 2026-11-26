# Spec Delta

## ADDED Requirements

### Requirement: The Installed CCCC CLI Explains Common Commands

`houmao-cccc --version` SHALL print the installed CLI distribution version and exit successfully. Top-level and command-specific help SHALL explain mode-specific usage. Help and version SHALL work without resolving a caller identity, opening a binding or profile, or connecting to a gateway or CCCC.

#### Scenario: Operator Checks an Installed Build

- **WHEN** an operator runs `houmao-cccc --version` from the installed distribution without a subcommand or connection configuration
- **THEN** the CLI reports the installed `houmao-cccc` distribution version and exits zero

#### Scenario: Agent Looks Up Common Gateway Commands

- **WHEN** an agent runs `houmao-cccc --help`
- **THEN** help gives exact gateway examples for `binding`, `members`, `chat send`, `chat reply`, `chat history`, and `chat deliveries`
- **AND THEN** it explains that the gateway instance selects the Group, that a gateway send takes the token from `members`, and where to find the handle for reply and receipt lookup
- **AND THEN** it shows direct-profile examples separately, with the target forms that apply to direct mode

#### Scenario: Agent Checks Which Receipt Target to Supply

- **WHEN** an agent runs `houmao-cccc chat deliveries --help`
- **THEN** help identifies `--handle` and `--event-ref` as gateway targets and `--event-id` as the direct target

### Requirement: CCCC CLI Reports Safe Usage Errors

The CLI SHALL report unsupported options and inapplicable delivery targets as actionable typed usage errors. Usage diagnostics SHALL identify the offending option where it can be safely named and omit user-supplied option values, credentials, private paths, message content, and raw exceptions.

#### Scenario: A Gateway Receipt Lookup Uses a Native Event ID

- **WHEN** a gateway-mode caller supplies `chat deliveries --event-id`
- **THEN** the CLI reports `gateway_delivery_requires_event_ref_or_handle` and points to `--handle` or `--event-ref` before contacting the gateway

#### Scenario: A Direct Receipt Lookup Uses a Gateway Target

- **WHEN** a direct-profile caller supplies `chat deliveries --handle` or `chat deliveries --event-ref`
- **THEN** the CLI reports `direct_delivery_requires_event_id` and points to `--event-id` before opening the profile or contacting CCCC

#### Scenario: A Command Receives an Unsupported Flag

- **WHEN** a caller supplies an unsupported option with a sensitive value in either separate or `--option=value` form
- **THEN** the CLI returns `unsupported_option`, names the safe option identifier, and directs the caller to help
- **AND THEN** the value is absent from the output

## MODIFIED Requirements

### Requirement: Membership Inspection Has Normal Actor Visibility

Membership inspection SHALL report only the selected Group's Actor-visible public membership and receive status. It SHALL NOT expose private runtime homes, execution credentials, or service administration operations. Unverified Houmao identities SHALL remain CCCC participants without synthesized agent IDs. `members --group` SHALL assert equality with the selected binding's Group before membership is read.

#### Scenario: Member Has No Houmao Identity Mapping

- **WHEN** a CCCC member is visible without a verified Houmao association
- **THEN** membership reports its CCCC Actor identity without hashing a name or address into an agent ID

#### Scenario: Agent Requests Private Member Configuration

- **WHEN** a caller requests another member's credentials or runtime environment
- **THEN** the integration reports an unsupported or forbidden operation without disclosing them

#### Scenario: The Expected Group Matches the Selected Binding

- **WHEN** an authorized gateway or direct caller runs `members` with a `--group` value equal to the selected Group
- **THEN** the result has the same visibility and shape as a `members` request with no assertion

#### Scenario: The Expected Group Differs From the Selected Binding

- **WHEN** an authorized caller asserts another Group through `members --group`
- **THEN** the CLI reports `group_conflict` and explains how to select the intended gateway instance or direct Actor profile
- **AND THEN** the integration returns no membership and issues no provider membership request

### Requirement: Delivery Lookup Returns Newest Attempts First

Gateway chat delivery lookup and the corresponding CLI command SHALL accept exactly one current message handle or scoped event reference. Direct CLI lookup SHALL accept exactly one native event ID and apply the selected Actor profile's visibility. Lookup SHALL report the retained attempts in reverse creation order, use the requested limit to select the newest matches, and set `has_more` when older matches were omitted.

#### Scenario: Sender Inspects a Refused Attempt and Its Accepted Retry

- **WHEN** the sender reads receipts for an event whose initial handoff was refused and whose explicit retry was accepted
- **THEN** the result lists the accepted retry before the refused original, with distinct provider attempt IDs for the same event
- **AND THEN** a limit of one returns the retry with `has_more` set to true

#### Scenario: Agent Reads Receipts by Message Handle

- **WHEN** an authorized gateway caller selects its incoming message by the handle in the request fence or its outgoing event by `event.handle` from a send or reply result
- **THEN** `GET /v1/plugins/{instance}/chat/deliveries?handle=HANDLE` and `houmao-cccc chat deliveries --handle HANDLE` return the same exact Actor-visible receipt projection as a valid reference for that event
- **AND THEN** the lookup submits no delivery claim, acknowledgement, or retry

#### Scenario: The Handle Belongs to a Nondefault Instance

- **WHEN** a CLI caller uses a valid handle without `--instance`
- **THEN** the CLI uses the handle's instance on the verified gateway
- **AND THEN** an explicit conflicting `--instance` fails before making the request

#### Scenario: Gateway Receives an Invalid Target Combination

- **WHEN** the gateway receives no receipt selector, both selector forms, a repeated selector, or a native event ID as the selector
- **THEN** it rejects the lookup with a typed usage error before requesting any provider receipts

#### Scenario: A Receipt Target Is Stale or Outside Its Scope

- **WHEN** a caller authorized for the selected receipt route submits a handle from an earlier gateway run or receiver generation, an expired handle, or a handle scoped to a different owner, instance, Actor binding, or Group
- **THEN** the gateway reports `message_handle_stale` with HTTP 409 before issuing a provider receipt lookup
- **AND THEN** the CLI guides the caller to select the event from authorized chat history

#### Scenario: A Receipt Reference Is Invalid or Outside Its Scope

- **WHEN** a caller submits a mistyped or out-of-scope gateway event reference
- **THEN** the gateway reports `reference_scope_error` with HTTP 422
- **AND THEN** the CLI guides the caller to select the event from authorized chat history
