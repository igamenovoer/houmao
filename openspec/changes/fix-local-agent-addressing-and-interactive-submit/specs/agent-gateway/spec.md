## ADDED Requirements

### Requirement: Gateway exposes semantic prompt submission separately from raw send-keys control

For gateway-managed tmux-backed sessions, the gateway SHALL keep semantic prompt submission separate from raw key/control-input delivery.

`POST /v1/requests` SHALL remain the semantic queued request surface for `submit_prompt` and `interrupt`.

The gateway SHALL additionally expose a dedicated raw control-input endpoint for send-keys style delivery. That endpoint SHALL accept exact `<[key-name]>` control-input sequences using the same contract as the runtime tmux-control-input capability, including optional full-string literal escaping.

The semantic gateway prompt path SHALL treat the provided prompt body as literal text, SHALL NOT interpret `<[key-name]>` substrings as special keys, and SHALL automatically submit once at the end.

The dedicated raw control-input endpoint SHALL NOT enqueue a durable `submit_prompt` request, SHALL NOT claim that a managed prompt turn was submitted, and SHALL NOT trigger gateway prompt-submission tracking hooks by itself.

#### Scenario: Gateway prompt submission remains on the queued semantic request surface

- **WHEN** a caller submits managed prompt work through the gateway
- **THEN** the caller uses `POST /v1/requests` with kind `submit_prompt`
- **AND THEN** the gateway treats that work as semantic prompt submission rather than generic key injection

#### Scenario: Gateway raw send-keys uses a separate control endpoint

- **WHEN** a caller needs to inject the raw control-input sequence `"/model<[Enter]><[Down]>"` into a live gateway-managed TUI
- **THEN** the caller uses the dedicated gateway raw control-input endpoint rather than `POST /v1/requests`
- **AND THEN** the gateway applies the exact `<[key-name]>` parsing rules without claiming that a semantic prompt turn was submitted

#### Scenario: Gateway send-prompt keeps special-key-looking text literal

- **WHEN** a caller submits gateway prompt text `type <[Enter]> literally`
- **THEN** the gateway semantic prompt path treats `<[Enter]>` as literal text
- **AND THEN** the gateway performs one automatic final submit instead of interpreting that substring as a raw keypress

### Requirement: Gateway semantic prompt submission for local interactive sessions uses the runtime semantic prompt path

When the gateway executes semantic prompt submission for an attached runtime-owned `local_interactive` session, it SHALL call the runtime semantic prompt-submission operation rather than routing prompt text through the raw send-keys control path.

For this local-interactive semantic prompt path, the gateway SHALL preserve the distinction between prompt submission and raw send-keys internally as well as on the HTTP surface.

The gateway SHALL only record gateway-owned prompt-submission tracking evidence after the semantic prompt-submission path succeeds.

#### Scenario: Gateway prompt for local interactive session uses semantic submit

- **WHEN** the gateway executes an accepted `submit_prompt` request for an attached runtime-owned `local_interactive` session
- **THEN** it calls the runtime semantic prompt-submission operation for that session
- **AND THEN** it does not implement that gateway prompt by sending raw prompt text plus Enter through the generic send-keys path

#### Scenario: Gateway raw send-keys does not create prompt-tracking evidence

- **WHEN** a caller uses the dedicated gateway raw control-input endpoint to send literal text or exact special-key tokens to an attached runtime-owned `local_interactive` session
- **THEN** the gateway does not invoke the semantic prompt-submission operation for that request
- **AND THEN** gateway-owned TUI prompt-tracking hooks do not record that raw control action as a submitted prompt turn

#### Scenario: Gateway raw send-keys does not auto-submit without explicit Enter

- **WHEN** a caller uses the dedicated gateway raw control-input endpoint to send the sequence `"hello world"` to an attached runtime-owned `local_interactive` session
- **THEN** the gateway inserts the literal text `hello world`
- **AND THEN** it does not auto-submit because the caller did not include an explicit `<[Enter]>`
