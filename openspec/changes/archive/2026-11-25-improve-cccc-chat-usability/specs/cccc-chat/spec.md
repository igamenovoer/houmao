# Spec Delta

## ADDED Requirements

### Requirement: CCCC CLI Diagnoses Gateway Endpoint and Managed-Self Selection

`houmao-cccc` SHALL use `--gateway-url` for the gateway base URL and `--instance` for the plugin namespace. It SHALL report distinct, actionable JSON errors for an invalid gateway URL and for unavailable verified managed-self authority. Both failures SHALL stop before making an HTTP request. Diagnostics SHALL use safe field names and fixed guidance.

#### Scenario: Agent Supplies the Advertised Plugin URL

- **WHEN** an agent passes the advertised `http://127.0.0.1:PORT/v1/plugins/INSTANCE` as `--gateway-url`
- **THEN** the CLI returns a nonzero exit with `invalid_gateway_url` and guidance to use the gateway base URL with `--instance` to select the plugin

#### Scenario: Gateway URL Contains Invalid or Private Input

- **WHEN** the supplied gateway URL is malformed or contains credentials
- **THEN** the CLI returns `invalid_gateway_url` and emits only safe diagnostics that exclude the input URL and raw exception text

#### Scenario: Current Managed Self Authority Cannot Be Selected

- **WHEN** a well-formed gateway base URL is supplied and the selected managed-self authority cannot be verified for it
- **THEN** the CLI returns a nonzero exit with `managed_self_authority_unavailable` and guidance to verify the current owning gateway and generation
- **AND THEN** the call ends under the selected caller identity before any signing or HTTP request

#### Scenario: Enrolled Caller Selects a Prefixed HTTPS Gateway

- **WHEN** an enrolled caller supplies the exact HTTPS base URL from its signer binding, including a configured proxy prefix
- **THEN** the CLI uses the shared gateway client's endpoint and signer checks and appends the selected plugin route under that prefix

### Requirement: Incoming Chat Identifies CLI Reply Inputs

An ordinary CCCC chat hint with resolved listener metadata SHALL distinguish the gateway base URL for the CLI from the local plugin URL for HTTP. It SHALL show the reply command using the selected plugin instance, current binding ID, opaque event reference, and a fresh caller operation ID.

#### Scenario: Agent Replies Through a Nondefault Instance

- **WHEN** the gateway hands off chat received through a plugin instance other than `cccc`
- **THEN** the hint identifies that instance and its gateway base and plugin URLs
- **AND THEN** the shown `houmao-cccc chat reply` syntax identifies the flags and values needed for a reply through the same owner binding

### Requirement: Delivery Lookup Returns Newest Attempts First

The gateway's CCCC chat delivery lookup and the corresponding CLI command SHALL present the provider's retained attempts for the selected event in reverse creation order. The requested limit SHALL select the newest matching attempts. The response SHALL use `has_more` to indicate that older matching attempts were omitted.

#### Scenario: Sender Inspects a Refused Attempt and Its Accepted Retry

- **WHEN** the sender reads receipts for an event whose initial handoff was refused and whose explicit retry was accepted
- **THEN** the result lists the accepted retry before the refused original, with distinct provider attempt IDs for the same event
- **AND THEN** a limit of one returns the retry with `has_more` set to true
