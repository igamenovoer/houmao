# kimi-web-control Specification

## Purpose

Specify the managed native Kimi browser host, authenticated control, and exact session and prompt identity.

## Requirements

### Requirement: Kimi Web binds one native browser and control session

A qualified `(kimi, web)` launch SHALL start `kimi web --no-open` in the selected private home and execution context. The owner SHALL verify the expected host, listener, native session, and workspace before declaring readiness. Public discovery SHALL expose a token-free browser handoff.

#### Scenario: Browser and gateway use the same conversation

- **WHEN** a person opens the verified native session and an authorized gateway addresses that session
- **THEN** both observe the same native conversation and retain independent client lifetimes

#### Scenario: The port belongs to another process

- **WHEN** the listener or host fails verification
- **THEN** the owner reports unavailable and withholds credentials and control input

### Requirement: Ordinary Kimi Web input checks readiness before sending

The owner SHALL serialize managed prompts, mailbox wakes, and plugin input. It SHALL check native readiness and current dispatch permission immediately before sending one native POST. The gateway SHALL preserve the native receipt when a browser changes readiness after the check.

#### Scenario: Active or queued work is visible at the final check

- **WHEN** the final readiness check observes busy, pending, or unavailable native state
- **THEN** the ordinary caller receives a refusal before the owner sends input

#### Scenario: A browser wins after the final check

- **WHEN** browser activity begins after the check and the native POST returns a queued receipt
- **THEN** the owner reports the exact managed request as queued and tracks its native prompt without submitting it again

### Requirement: Observation and interruption address exact native work

Kimi Web inspection SHALL retain native origin, session, prompt identity, and actual queue or terminal state. Passive reads SHALL avoid cold activation. Interruption SHALL target the exact verified prompt.

#### Scenario: The browser starts a turn

- **WHEN** the owner observes a native prompt outside its managed correlation
- **THEN** the observation remains external or of unknown origin and cannot settle an unrelated managed request

#### Scenario: The submission response is lost

- **WHEN** Kimi may have accepted the original POST
- **THEN** the owner reconciles that prompt identity or reports uncertainty without replay

### Requirement: Lifecycle preserves private access and exact continuity

Gateway reattachment SHALL use the verified native host and session. Stop and relaunch SHALL obey the saved owner authority. Native tokens and access-bearing URL fragments SHALL stay outside public handoff, shared records, and logs.

#### Scenario: Gateway is replaced during browser use

- **WHEN** the gateway reconnects to the same live host and session
- **THEN** the browser remains connected and the gateway can inspect exact managed work

#### Scenario: Relaunch selects the saved session

- **WHEN** an operator requests exact continuation after stopping the host
- **THEN** the owner verifies the new host and saved session and refuses stale prompt handles

### Requirement: An owned Kimi Web host supports gateway browser sign-in

The Kimi Web backend SHALL supply the owning gateway with a verified native browser destination using Kimi's token fragment. The destination SHALL use a qualified session path when the installed build supports it and use the verified native root when the browser must select the session in its UI.

#### Scenario: A fresh browser enters through the gateway

- **WHEN** an operator redeems a valid ticket for a supported live Kimi Web agent
- **THEN** the native UI uses its fragment authentication to open an authenticated browser session
- **AND THEN** the browser reaches the bound conversation through the qualified link or explicit native selection
- **AND THEN** Houmao's API binding remains independent of browser authentication

#### Scenario: Kimi host identity has changed

- **WHEN** listener, host, or conversation verification fails before redemption
- **THEN** the backend withholds the private browser destination
