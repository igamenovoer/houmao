## MODIFIED Requirements

### Requirement: CAO REST client matches the vendored CAO API contract
The system SHALL implement a CAO REST client whose request parameter names,
parameter locations, and response shapes match the vendored CAO server API
(`extern/orphan/cli-agent-orchestrator/docs/api.md` and server implementation).

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

### Requirement: CAO backend uses tmux session env for allowlisted credential propagation
When using the CAO backend, the system SHALL apply allowlisted credential
environment variables by configuring a unique tmux session environment before
spawning the CAO terminal into that session.

For supported loopback CAO base URLs, the tmux session environment SHALL
preserve proxy variables (for agent egress) and SHALL include loopback entries
in `NO_PROXY`/`no_proxy` by default (merge+append semantics).

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the system SHALL NOT modify `NO_PROXY`
or `no_proxy` and will respect caller-provided values.

#### Scenario: CAO launch configures tmux env before spawning terminal
- **WHEN** the runtime launches a CAO-backed session with a launch plan that includes a tool home selector env var and allowlisted credential env vars
- **THEN** the runtime creates a unique tmux session for that runtime session
- **AND THEN** the runtime sets the home selector env var and allowlisted credential env vars in that tmux session environment
- **AND THEN** the runtime creates the CAO terminal in that tmux session via `POST /sessions/{session_name}/terminals`

#### Scenario: Loopback tmux env preserves proxy vars and injects loopback `NO_PROXY` by default
- **WHEN** the runtime launches a CAO-backed session against a supported loopback CAO base URL
- **AND WHEN** caller environment includes `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` (including lowercase variants)
- **THEN** the created tmux session environment preserves those proxy variables for agent egress
- **AND THEN** the created tmux session environment includes `NO_PROXY` and `no_proxy` entries covering `localhost`, `127.0.0.1`, and `::1` by default

#### Scenario: Preserve mode does not modify tmux `NO_PROXY`
- **WHEN** the runtime launches a CAO-backed session against a supported loopback CAO base URL
- **AND WHEN** caller environment includes `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`
- **THEN** the created tmux session environment does not inject or modify `NO_PROXY`/`no_proxy`
