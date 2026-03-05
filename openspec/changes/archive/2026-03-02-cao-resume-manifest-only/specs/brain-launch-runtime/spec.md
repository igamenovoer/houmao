## MODIFIED Requirements

### Requirement: Optional CAO backend via REST boundary
The system SHALL optionally support launching and driving sessions via CAO using CAO's REST API, without requiring the core runtime to depend on CAO internals.

#### Scenario: CAO-backed session launch and messaging
- **WHEN** a developer starts a CAO-backed session and provides a CAO API base URL at session start
- **THEN** the system creates a CAO session/terminal, sends prompts, and fetches replies using CAO REST endpoints
- **AND THEN** the system persists the CAO API base URL and terminal identity in the session manifest
- **AND THEN** subsequent prompt and stop operations target the CAO terminal using only the persisted session manifest fields (no CAO base URL override)

### Requirement: Persist a session manifest JSON
The system SHALL persist a session manifest JSON (session handle) alongside the brain manifest for audit/resume/stop.

#### Scenario: Start session writes a session manifest
- **WHEN** a developer starts a session
- **THEN** the system writes a session manifest JSON that records the backend type and the minimal reconnect/stop fields (e.g., process identity for long-lived backends, `session_id` for resumable headless backends, terminal IDs and CAO API base URL for CAO, artifact paths, working directory)

#### Scenario: Resume headless session from persisted manifest
- **WHEN** a developer resumes a Claude/Gemini session from a persisted session manifest
- **THEN** the system uses the persisted `session_id` with backend resume flags for the next prompt
- **AND THEN** if required resume fields are missing or invalid, the system returns an explicit resume error instead of silently starting an unrelated new conversation

#### Scenario: Resume CAO session from persisted manifest
- **WHEN** a developer sends a prompt or stops a CAO-backed session using a persisted session manifest
- **THEN** the system targets the CAO terminal using the persisted `cao.api_base_url` and `cao.terminal_id`
- **AND THEN** the operation does not require (and does not accept) an external CAO base URL override
