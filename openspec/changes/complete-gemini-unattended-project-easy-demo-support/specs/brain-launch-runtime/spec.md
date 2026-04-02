## MODIFIED Requirements

### Requirement: Runtime refuses startup-prompt-forbidden launch when policy cannot be satisfied
The system SHALL fail before provider process start when a requested startup-prompt-forbidden launch policy cannot be satisfied for the detected tool version, backend, or launch context.

That failure SHALL preserve enough structured detail for higher-level launch surfaces to report that backend selection completed but provider startup was blocked by launch-policy compatibility.

#### Scenario: Unsupported version blocks unattended launch before provider start
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** no compatible strategy exists for the detected tool version and backend under the declared supported-version ranges
- **THEN** the runtime fails the launch before starting the provider process
- **AND THEN** the error identifies the requested policy, tool, backend, and detected version
- **AND THEN** higher-level callers can distinguish that no provider process was started

#### Scenario: Backend without a compatible unattended strategy fails closed
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** no compatible unattended strategy exists for the selected backend and detected tool version
- **THEN** the runtime fails the launch before starting the provider process
- **AND THEN** the error identifies the requested policy, tool, backend, and why no compatible strategy could be selected

## ADDED Requirements

### Requirement: Gemini headless runtime honors unattended launch policy when compatible registry coverage exists
When a session requests `operator_prompt_mode = unattended` on the `gemini_headless` backend and a compatible Gemini launch-policy strategy exists for the detected Gemini CLI version, the runtime SHALL apply that strategy before provider process start and SHALL allow Gemini startup to continue on the maintained unattended path.

#### Scenario: Compatible Gemini unattended strategy enables headless provider start
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** the selected backend is `gemini_headless`
- **AND WHEN** the detected Gemini CLI version matches one compatible maintained Gemini strategy
- **THEN** the runtime applies the Gemini unattended strategy before provider start
- **AND THEN** Gemini startup continues on the unattended headless path instead of failing only because the backend is Gemini
