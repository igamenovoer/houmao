## Purpose
Define requirements for the repo-owned CAO REST client contract and related CAO backend behaviors (typed parsing, tmux env propagation, and provider mapping).
## Requirements
### Requirement: CAO REST client matches the vendored CAO API contract
The system SHALL implement a CAO-compatible REST client whose request parameter names, parameter locations, and response shapes match the pinned CAO server API contract.

For supported loopback compatibility base URLs, the CAO-compatible REST client SHALL bypass ambient proxy environment variables by default by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`.

When `HOUMAO_PRESERVE_NO_PROXY_ENV=1`, the CAO-compatible REST client SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

#### Scenario: Loopback compatibility requests bypass ambient proxy env on a non-default port
- **WHEN** the CAO-compatible client is configured with pair root base URL `http://127.0.0.1:9990`
- **AND WHEN** caller environment includes `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`
- **THEN** client requests to the loopback compatibility authority bypass those proxy endpoints by default

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
When using the CAO backend, the system SHALL apply allowlisted credential environment variables by configuring a unique tmux session environment before spawning the CAO terminal into that session.

For supported loopback CAO base URLs, the tmux session environment SHALL preserve proxy variables for agent egress and SHALL include loopback entries in `NO_PROXY` and `no_proxy` by default.

When `HOUMAO_PRESERVE_NO_PROXY_ENV=1`, the system SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

#### Scenario: Preserve mode does not modify tmux `NO_PROXY`
- **WHEN** the runtime launches a CAO-backed session against a supported loopback CAO base URL
- **AND WHEN** caller environment includes `HOUMAO_PRESERVE_NO_PROXY_ENV=1`
- **THEN** the created tmux session environment does not inject or modify `NO_PROXY` or `no_proxy`

### Requirement: Runtime-generated CAO profiles include required metadata
When using Houmao's CAO-compatible control path, the system SHALL render and store compatibility agent profiles that conform to the pinned CAO agent-profile format and can be loaded by Houmao-owned provider adapters without validation errors.

Those compatibility profiles SHALL live in a Houmao-managed profile store rather than in a caller-managed standalone CAO `HOME`.

#### Scenario: Rendered compatibility profile includes required YAML frontmatter fields
- **WHEN** the system generates a compatibility agent profile for role `R`
- **THEN** the YAML frontmatter includes `name` and `description` as non-empty strings
- **AND THEN** Houmao-owned compatibility profile loading accepts the rendered profile successfully

#### Scenario: Pair install writes compatibility profile into Houmao-managed store
- **WHEN** a pair-owned install flow stores a compatibility profile for provider `codex`
- **THEN** the resulting profile artifact is written into the Houmao-managed profile store
- **AND THEN** callers do not need to manage a separate CAO-home profile directory as part of the supported pair contract

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

### Requirement: CAO REST client exposes overrideable operational timeout budgets
The system SHALL expose supported operational timeout configuration for the repo-owned CAO-compatible REST client rather than relying on one unoverrideable flat timeout budget for every request.

At minimum, the client contract SHALL distinguish between:

- a general request timeout budget
- a create-operation timeout budget

The default general request timeout SHALL be 15 seconds.

The default create-operation timeout SHALL be 75 seconds.

The create-operation timeout SHALL apply to:

- `POST /sessions`
- `POST /sessions/{session_name}/terminals`

Other client requests SHALL continue using the general request timeout unless a later change defines a more specific budget.

Direct Python callers SHALL be able to override both budgets through supported client construction or call configuration without patching repository source.

#### Scenario: Default client uses split timeout budgets
- **WHEN** a caller uses the default CAO-compatible client configuration
- **THEN** lightweight requests such as health, list, detail, input, output, and delete use a 15-second timeout budget
- **AND THEN** session and terminal creation requests use a 75-second timeout budget

#### Scenario: Explicit client override changes create budget without widening other requests
- **WHEN** a caller constructs the CAO-compatible client with `timeout_seconds = 5` and `create_timeout_seconds = 90`
- **THEN** lightweight requests use a 5-second timeout budget
- **AND THEN** `create_session()` and `create_terminal()` use a 90-second timeout budget

