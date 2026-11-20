# Spec Delta

## ADDED Requirements

### Requirement: The scoped gateway CLI requests a Web entry URL

`houmao-mgr agents single --agent-id <id> gateway web-entry` SHALL request a browser ticket from the selected agent's live owner-local gateway using its enrolled admin signer. The command SHALL return `url` and `expires_at_utc` without following the URL. Help SHALL describe the URL as a bearer secret.

#### Scenario: An operator requests an entry URL

- **WHEN** the command targets a live supported managed Web agent with an available admin signer
- **THEN** the command prints the gateway ticket URL and its expiry
- **AND THEN** its output contains no native launch token, browser cookie, or private bootstrap path

#### Scenario: Gateway entry authority is unavailable

- **WHEN** the selected gateway is detached, the signer is missing or rejected, or the target requires an unsupported proxy or executor route
- **THEN** the command returns actionable owner-local guidance
- **AND THEN** it performs no unsigned retry, automatic attach, or native credential fallback
