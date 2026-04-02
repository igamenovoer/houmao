## ADDED Requirements

### Requirement: Gemini headless startup supports API-key and OAuth auth families
When the runtime constructs a Gemini headless home, the system SHALL support these Gemini auth families for headless startup:

- API key mode using `GEMINI_API_KEY`
- API key mode with optional `GOOGLE_GEMINI_BASE_URL`
- OAuth mode using projected `oauth_creds.json`

#### Scenario: Gemini API-key launch projects the API key into the headless runtime
- **WHEN** the runtime builds a Gemini headless home from an auth bundle that provides `GEMINI_API_KEY`
- **THEN** the launched Gemini process receives that API key through the supported runtime environment contract
- **AND THEN** the first Gemini headless turn can start non-interactively without requiring OAuth-specific runtime files

#### Scenario: Gemini API-key launch preserves an explicit endpoint override
- **WHEN** the runtime builds a Gemini headless home from an auth bundle that provides both `GEMINI_API_KEY` and `GOOGLE_GEMINI_BASE_URL`
- **THEN** the launched Gemini process receives both values through the supported runtime environment contract
- **AND THEN** the runtime does not drop the configured Gemini endpoint override during headless startup

### Requirement: Gemini OAuth-backed runtime homes are non-interactive-ready for headless startup
When the runtime constructs a Gemini headless home from OAuth-backed credential material, the system SHALL make the launched Gemini process non-interactive-ready without depending on prior user-global interactive Gemini setup state.

#### Scenario: Fresh Gemini OAuth home selects the Google-login auth path automatically
- **WHEN** the runtime builds a Gemini headless home that projects `oauth_creds.json`
- **AND WHEN** the effective Gemini launch environment does not already select API-key auth
- **THEN** the runtime exports the Gemini auth selector needed for Google-login OAuth headless startup
- **AND THEN** the first headless Gemini turn can start non-interactively without requiring a pre-existing user-global `settings.json`

#### Scenario: Explicit API-key Gemini auth selection is preserved
- **WHEN** the effective Gemini launch environment explicitly selects API-key auth
- **THEN** the runtime does not override that selection only because an OAuth credential file is present

### Requirement: Gemini managed skill projection uses the generic `.agents/skills` root
When Houmao projects Gemini skills into a managed Gemini home or performs default Houmao-owned Gemini skill installation for an adopted session, the system SHALL use `.agents/skills` as the discoverable Gemini skill root.

#### Scenario: Constructed Gemini home projects selected skills into `.agents/skills`
- **WHEN** the runtime builds a Gemini managed home with one or more selected skills
- **THEN** the projected Gemini skills are created under `.agents/skills` in that managed home
- **AND THEN** the runtime does not target `.gemini/skills` as the primary Gemini skills destination for that managed home

#### Scenario: Default Gemini join-time skill installation uses `.agents/skills`
- **WHEN** Houmao adopts a Gemini session and performs the default Houmao-owned skill projection for that session
- **THEN** the installed Gemini skills are created under the adopted session's `.agents/skills` root
- **AND THEN** the default projection contract does not require a parallel mirror under `.gemini/skills`

## MODIFIED Requirements

### Requirement: Gemini headless backend via `gemini -p` + `--resume`
For Gemini, the system SHALL support a non-CAO interactive backend using repeated headless CLI invocations with machine-readable output and session resume.

The runtime SHALL:

- start Gemini headless turns using machine-readable Gemini headless output,
- capture the returned Gemini `session_id` from the first successful headless turn,
- persist that Gemini `session_id` in the session manifest, and
- resume subsequent Gemini turns using `--resume <session_id>` in the same recorded working directory/project context.

#### Scenario: Start Gemini headless session and persist the returned `session_id`
- **WHEN** a developer starts a Gemini session in headless mode and sends a first prompt using a constructed brain home
- **THEN** the system captures the returned Gemini `session_id` from machine-readable Gemini output
- **AND THEN** the system persists that `session_id` in the session manifest

#### Scenario: Follow-up Gemini turn resumes by exact persisted session id
- **WHEN** a developer sends a follow-up prompt to a Gemini headless session
- **AND WHEN** the session manifest contains a persisted Gemini `session_id`
- **THEN** the system resumes Gemini with `--resume <session_id>`
- **AND THEN** the system does not substitute `--resume latest` for that follow-up turn

#### Scenario: Gemini resume uses the recorded project context
- **WHEN** a developer resumes a Gemini headless session from a persisted session manifest
- **THEN** the resumed turn uses the same working directory/project context recorded in the session manifest
- **AND THEN** the runtime returns an explicit error instead of silently resuming from a different project context
