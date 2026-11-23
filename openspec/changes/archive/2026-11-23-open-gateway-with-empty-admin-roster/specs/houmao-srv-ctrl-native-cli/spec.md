# houmao-srv-ctrl-native-cli Delta

## MODIFIED Requirements

### Requirement: The scoped gateway CLI requests a Web entry URL

`houmao-mgr agents single --agent-id <id> gateway web-entry` SHALL use the live owner-local gateway. It SHALL request a ticket unsigned under verified open policy and use an enrolled admin signer under keyed policy. The command SHALL return `url` and `expires_at_utc` without following the URL. Help SHALL describe it as a bearer secret.

#### Scenario: An operator requests an entry URL

- **WHEN** the command targets a live supported managed Web agent with an available admin signer
- **THEN** the command prints the gateway ticket URL and its expiry
- **AND THEN** its output contains no native launch token, browser cookie, or private bootstrap path

#### Scenario: Gateway entry authority is unavailable

- **WHEN** the selected gateway is detached, its policy is unavailable, the required signer is missing or rejected, or the target requires an unsupported proxy or executor route
- **THEN** the command returns actionable owner-local guidance
- **AND THEN** it performs no unsigned retry, automatic attach, or native credential fallback

#### Scenario: An operator requests a link on an open gateway

- **WHEN** the selected live owner-local Web gateway reports open policy for the current execution
- **THEN** the command requests and prints the one-time link and expiry without requiring a signer
- **AND THEN** the gateway independently checks the live roster before issuance

#### Scenario: Enrollment races the unsigned CLI request

- **WHEN** the roster gains a key after the command reads open policy and before ticket issuance
- **THEN** the command surfaces the refusal and ends the attempt
