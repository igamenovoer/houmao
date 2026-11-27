# Spec Delta

## ADDED Requirements

### Requirement: Managed Fixture Qualification Verifies Maximum Unattended Permissions

Qualification SHALL observe the effective maximum qualified native posture across the supported managed provider and run-mode combinations. Qualification SHALL distinguish observed native behavior from configuration intent and record unsupported combinations and missing prerequisites separately from passes.

#### Scenario: Each Managed Mode Uses Its Own Qualified Native Controls

- **WHEN** a fixture qualifies unattended launch for a supported managed provider and mode
- **THEN** it records the observed native permission posture and verifies representative work without operator approval
- **AND THEN** it exercises the same launch policy on explicit relaunch where that mode supports relaunch

#### Scenario: Conflicting Settings Fail Before Replacing a Runtime

- **WHEN** qualification supplies an authored permission setting that conflicts with unattended maximum permissions
- **THEN** the maintained launch path reports the conflict before starting a provider or replacing a running agent
- **AND THEN** an equivalent supported setting remains usable through `as_is`

### Requirement: Managed Hermes Fixtures Qualify Native Approval and Mail Behavior

Managed Hermes qualification SHALL exercise unattended TUI, service, and headless tool handling, manual TUI approval observation, and the live Stalwart mail round trip. The result SHALL identify each lane's native evidence, provider build, and unavailable prerequisites without exposing credentials or approval payloads.

#### Scenario: A Live Unattended TUI Completes the Stalwart Notifier Round

- **WHEN** a verified unattended Hermes TUI receives a Stalwart mail notifier prompt that invokes an otherwise approval-gated command
- **THEN** the TUI handles the command without operator input
- **AND THEN** the sender receives the expected reply and mailbox state confirms that the recipient archived the request

#### Scenario: The ACP Service Completes a Structured Edit

- **WHEN** an unattended managed Hermes ACP service receives a prompt that uses a native structured file-edit tool
- **THEN** qualification verifies the native tool call and its expected file effect without operator approval or fallback to terminal redirection
- **AND THEN** controlled protocol checks distinguish a qualified one-time tool grant from a refusal or cancelled user interaction

#### Scenario: A Finite Headless Client Continues With Unattended Permissions

- **WHEN** qualification sends approval-gated work to an unattended headless fixture and then continues its verified conversation
- **THEN** both turns settle through finite structured CLI evidence without an operator and retain the same logical conversation

#### Scenario: A Manual TUI Reports a Verified Pending Approval

- **WHEN** a managed `as_is` Hermes TUI is waiting at a native tool approval
- **THEN** qualification observes the safe pending state and closed readiness, with terminal attachment reported separately
- **AND THEN** state clears the indicator after verified settlement
