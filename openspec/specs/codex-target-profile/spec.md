## ADDED Requirements

### Requirement: Codex Capture Profile
The system SHALL provide a CaptureProfile for the codex agent system.

#### Scenario: Define Codex Reverse Proxies
- **WHEN** the codex capture profile is loaded
- **THEN** it defines two reverse proxies:
  - Port 8080 upstream to `https://api.openai.com/` (Model API)
  - Port 8081 upstream to `https://chatgpt.com/` (Backend channels)

#### Scenario: Define Codex Environment Overrides
- **WHEN** the codex capture profile is loaded
- **THEN** it sets `OPENAI_BASE_URL` to `http://127.0.0.1:8080/v1`

#### Scenario: Define Codex Manual Steps
- **WHEN** the codex capture profile is loaded
- **THEN** it includes a manual step to set `chatgpt_base_url` in `~/.codex/config.toml`

#### Scenario: Define Codex Output Directory
- **WHEN** the codex capture profile is loaded
- **THEN** it sets the output directory to `tmp/codex-traffic`

### Requirement: Codex Analysis Profile
The system SHALL provide an AnalysisProfile for the codex agent system.

#### Scenario: Use OpenAI Body Renderers
- **WHEN** the codex analysis profile is loaded
- **THEN** it uses the OpenAI Responses API request and response body renderers

#### Scenario: Define Codex Header Redaction
- **WHEN** the codex analysis profile is loaded
- **THEN** it redacts `authorization`, `cookie`, `set-cookie`, and `openai-organization` headers

### Requirement: Codex Target Discovery
The system SHALL allow the codex target to be loaded by name.

#### Scenario: Load Codex By Name
- **WHEN** a tool is invoked with `--target codex`
- **THEN** the system loads the codex capture and analysis profiles from the `targets/codex` module
