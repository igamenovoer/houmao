## Purpose
Define requirements for the repo-owned CAO REST client contract and related CAO backend behaviors (typed parsing, tmux env propagation, and provider mapping).
## Requirements
### Requirement: CAO REST client matches the vendored CAO API contract
The system SHALL implement a CAO REST client whose request parameter names,
parameter locations, and response shapes match the vendored CAO server API
(`extern/orphan/cli-agent-orchestrator/docs/api.md` and server implementation).

For supported loopback CAO base URLs (`http://localhost:<port>`,
`http://127.0.0.1:<port>` with explicit ports), the CAO REST client SHALL
bypass ambient proxy environment variables by default by ensuring loopback
entries exist in `NO_PROXY`/`no_proxy`.

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

#### Scenario: Loopback CAO requests bypass ambient proxy env on a non-default port
- **WHEN** the CAO REST client is configured with loopback base URL `http://127.0.0.1:9991`
- **AND WHEN** caller environment includes `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`
- **THEN** client requests to that loopback CAO endpoint bypass those proxy endpoints by default

#### Scenario: Preserve mode respects caller `NO_PROXY` behavior
- **WHEN** the CAO REST client is configured with a supported loopback base URL
- **AND WHEN** caller environment includes `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`
- **THEN** the CAO REST client does not inject or modify `NO_PROXY`/`no_proxy`
- **AND THEN** proxy routing behavior for loopback depends on the caller-provided proxy env values

### Requirement: CAO REST responses are parsed into typed models
The system SHALL parse CAO REST JSON responses into typed models (Pydantic) for at least terminal status and output.

The terminal `status` field SHALL remain validated against CAO's known terminal status values.

The terminal `provider` field SHALL be treated as a non-empty provider identifier string returned by CAO rather than a repo-owned closed enum. New upstream provider identifiers SHALL parse successfully without requiring a local model update before unrelated fields can be consumed.

The `CaoProvider` enum type SHALL NOT remain the Pydantic response-model field type or public typed response contract for terminal `provider`.

#### Scenario: Terminal status is a validated enum
- **WHEN** the runtime fetches `GET /terminals/{TERM_ID}`
- **THEN** the parsed terminal response exposes a `status` value validated against CAO’s known terminal statuses (for example `idle`, `processing`, `completed`, `waiting_user_answer`, `error`)

#### Scenario: Unknown upstream provider id still parses
- **WHEN** the runtime fetches `GET /terminals/{TERM_ID}`
- **AND WHEN** CAO returns terminal `provider = "kimi_cli"`
- **THEN** the parsed terminal response preserves `provider = "kimi_cli"`
- **AND THEN** parsing does not fail solely because that provider identifier was not predeclared in repo-owned code

### Requirement: CAO backend uses tmux session env for allowlisted credential propagation
When using the CAO backend, the system SHALL apply allowlisted credential
environment variables by configuring a unique tmux session environment before
spawning the CAO terminal into that session.

For supported loopback CAO base URLs (`http://localhost:<port>`,
`http://127.0.0.1:<port>` with explicit ports), the tmux session environment
SHALL preserve proxy variables (for agent egress) and SHALL include loopback
entries in `NO_PROXY`/`no_proxy` by default (merge+append semantics).

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the system SHALL NOT modify `NO_PROXY`
or `no_proxy` and will respect caller-provided values.

#### Scenario: CAO launch configures tmux env before spawning terminal
- **WHEN** the runtime launches a CAO-backed session with a launch plan that includes a tool home selector env var and allowlisted credential env vars
- **THEN** the runtime creates a unique tmux session for that runtime session
- **AND THEN** the runtime sets the home selector env var and allowlisted credential env vars in that tmux session environment
- **AND THEN** the runtime creates the CAO terminal in that tmux session via `POST /sessions/{session_name}/terminals`

#### Scenario: Loopback tmux env preserves proxy vars and injects loopback `NO_PROXY` by default on a non-default port
- **WHEN** the runtime launches a CAO-backed session against loopback base URL `http://localhost:9991`
- **AND WHEN** caller environment includes `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` (including lowercase variants)
- **THEN** the created tmux session environment preserves those proxy variables for agent egress
- **AND THEN** the created tmux session environment includes `NO_PROXY` and `no_proxy` entries covering `localhost`, `127.0.0.1`, and `::1` by default

#### Scenario: Preserve mode does not modify tmux `NO_PROXY`
- **WHEN** the runtime launches a CAO-backed session against a supported loopback CAO base URL
- **AND WHEN** caller environment includes `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`
- **THEN** the created tmux session environment does not inject or modify `NO_PROXY`/`no_proxy`

### Requirement: Runtime-generated CAO profiles include required metadata
When using the CAO backend, the system SHALL render a runtime-generated CAO agent profile markdown that conforms to the vendored CAO agent profile format (`extern/orphan/cli-agent-orchestrator/docs/agent-profile.md`) and can be loaded by CAO without validation errors.

#### Scenario: Rendered CAO profile includes required YAML frontmatter fields
- **WHEN** the runtime generates a CAO agent profile for role `R`
- **THEN** the YAML frontmatter includes `name` and `description` as non-empty strings
- **AND THEN** CAO is able to load the generated profile successfully (for example it does not fail with a missing required field like `description`)

### Requirement: CAO backend provider mapping is explicit and validated
The system SHALL map runtime tool identities to CAO provider identifiers explicitly at launch time and fail fast for unsupported tools.

Parsing a CAO response that contains a provider identifier SHALL NOT widen the set of runtime-supported CAO launch targets by itself.

#### Scenario: CAO provider mapping for codex and claude
- **WHEN** the runtime launches a CAO-backed session for tool `codex`
- **THEN** it uses CAO provider `codex`
- **AND WHEN** the runtime launches a CAO-backed session for tool `claude`
- **THEN** it uses CAO provider `claude_code`

#### Scenario: Unsupported CAO tool fails fast
- **WHEN** the runtime is asked to launch a CAO-backed session for a tool that has no CAO provider mapping
- **THEN** the runtime fails with an explicit error describing the unsupported tool/provider mapping

#### Scenario: Parsed provider id does not imply launch support
- **WHEN** the runtime successfully parses a CAO terminal response whose provider id is `kimi_cli`
- **AND WHEN** the runtime is later asked to launch a CAO-backed session for tool `kimi`
- **THEN** the runtime still rejects that launch request with an explicit unsupported tool/provider mapping error

### Requirement: Live demo scripts prove end-to-end prompt processing with real providers
In addition to unit tests, the repo SHALL include opt-in demo tutorial packs under `scripts/demo/<purpose-slug>/...` that demonstrate launching sessions and processing prompts end-to-end against real cloud providers using local credential profiles under `agents/brains/api-creds/`.

Each demo SHALL follow the tutorial-pack guidance in `magic-context/instructions/explain/make-api-tutorial-pack.md` (step-by-step README, one-click `run_demo.sh`, temporary workspace, tracked minimal inputs, and a verification story via `expected_report/` + sanitizer or an explicit verifier).

#### Scenario: Codex CAO demo launches and returns a real response
- **WHEN** a developer runs the Codex CAO demo script with valid Codex/OpenAI credentials present under `agents/brains/api-creds/`
- **AND WHEN** `cao-server` is running locally
- **THEN** the demo launches a CAO-backed Codex session, sends a prompt, and receives a non-empty model response

#### Scenario: Claude Code CAO demo launches and returns a real response
- **WHEN** a developer runs the Claude Code CAO demo script with valid Claude/Anthropic credentials present under `agents/brains/api-creds/`
- **AND WHEN** `cao-server` is running locally
- **THEN** the demo launches a CAO-backed Claude Code session, sends a prompt, and receives a non-empty model response

#### Scenario: Gemini demo launches and returns a real response
- **WHEN** a developer runs the Gemini demo script with valid Gemini credentials present under `agents/brains/api-creds/`
- **THEN** the demo launches a Gemini session (using the runtime’s supported non-CAO backend) and receives a non-empty model response

#### Scenario: Demo tutorial pack has the required structure
- **WHEN** a developer inspects a demo under `scripts/demo/<purpose-slug>/`
- **THEN** it includes a `README.md` and a `run_demo.sh`
- **AND THEN** it uses a temporary workspace under `tmp/` (or another gitignored path)

#### Scenario: Missing credentials causes a demo to skip
- **WHEN** a developer runs an individual demo script
- **AND WHEN** the required credential profile files under `agents/brains/api-creds/` are missing
- **THEN** the demo reports SKIP with an actionable reason
- **AND THEN** the demo exits successfully without attempting provider calls

#### Scenario: Invalid credentials causes a demo to skip
- **WHEN** a developer runs an individual demo script
- **AND WHEN** the provider rejects the request due to invalid/unauthorized credentials
- **THEN** the demo reports SKIP with an actionable reason
- **AND THEN** the demo exits successfully without marking the overall demo suite as failed

#### Scenario: Connectivity loss causes a demo to skip
- **WHEN** a developer runs an individual demo script
- **AND WHEN** the demo cannot reach a required service (for example CAO server connection failure, network error, or provider timeout)
- **THEN** the demo reports SKIP with an actionable reason
- **AND THEN** the demo exits successfully without marking the overall demo suite as failed
