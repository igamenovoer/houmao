## MODIFIED Requirements

### Requirement: CAO REST client matches the vendored CAO API contract
The system SHALL implement a CAO REST client whose request parameter names,
parameter locations, and response shapes match the CAO fork server API and
server implementation referenced by active `gig-agents` guidance.

For supported loopback CAO base URLs (`http://localhost:9889`,
`http://127.0.0.1:9889`), the CAO REST client SHALL bypass ambient proxy
environment variables by default by ensuring loopback entries exist in
`NO_PROXY`/`no_proxy`.

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the CAO REST client SHALL NOT modify
`NO_PROXY` or `no_proxy` and will respect caller-provided values (for example,
to allow traffic-watching development proxies like mitmproxy).

#### Scenario: Create terminal uses CAO query parameters
- **WHEN** the runtime requests creation of a CAO terminal in session `S` for provider `P`, agent profile `A`, and working directory `W`
- **THEN** the CAO REST client issues a `POST /sessions/{S}/terminals` request using CAO’s parameter names (`provider`, `agent_profile`, `working_directory`)
- **AND THEN** the client does not send incompatible JSON payload keys (for example `profile` or `text`)

#### Scenario: Send terminal input uses CAO message parameter
- **WHEN** the runtime sends input text `T` to terminal `TERM_ID`
- **THEN** the CAO REST client issues `POST /terminals/{TERM_ID}/input` using CAO’s parameter name `message=T`

#### Scenario: Get terminal output parses CAO output response
- **WHEN** the runtime requests `GET /terminals/{TERM_ID}/output?mode=last`
- **THEN** the CAO REST client returns the response `output` string as the terminal output text

#### Scenario: Loopback CAO requests bypass ambient proxy env
- **WHEN** the CAO REST client is configured with a supported loopback base URL
- **AND WHEN** caller environment includes `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`
- **THEN** client requests to loopback CAO endpoints bypass those proxy endpoints by default

#### Scenario: Preserve mode respects caller `NO_PROXY` behavior
- **WHEN** the CAO REST client is configured with a supported loopback base URL
- **AND WHEN** caller environment includes `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`
- **THEN** the CAO REST client does not inject or modify `NO_PROXY`/`no_proxy`
- **AND THEN** proxy routing behavior for loopback depends on the caller-provided proxy env values

### Requirement: Runtime-generated CAO profiles include required metadata
When using the CAO backend, the system SHALL render a runtime-generated CAO
agent profile markdown that conforms to the CAO fork agent profile format
referenced by active `gig-agents` guidance and can be loaded by CAO without
validation errors.

#### Scenario: Rendered CAO profile includes required YAML frontmatter fields
- **WHEN** the runtime generates a CAO agent profile for role `R`
- **THEN** the YAML frontmatter includes `name` and `description` as non-empty strings
- **AND THEN** CAO is able to load the generated profile successfully (for example it does not fail with a missing required field like `description`)
