## MODIFIED Requirements

### Requirement: CAO REST responses are parsed into typed models
The system SHALL parse CAO REST JSON responses into typed models (Pydantic) for at least terminal status and output.

The terminal `status` field SHALL remain validated against CAO's known terminal
status values.

The terminal `provider` field SHALL be treated as a non-empty provider
identifier string returned by CAO rather than a repo-owned closed enum. New
upstream provider identifiers SHALL parse successfully without requiring a
local model update before unrelated fields can be consumed.

#### Scenario: Terminal status is a validated enum
- **WHEN** the runtime fetches `GET /terminals/{TERM_ID}`
- **THEN** the parsed terminal response exposes a `status` value validated against CAO’s known terminal statuses (for example `idle`, `processing`, `completed`, `waiting_user_answer`, `error`)

#### Scenario: Unknown upstream provider id still parses
- **WHEN** the runtime fetches `GET /terminals/{TERM_ID}`
- **AND WHEN** CAO returns terminal `provider = "kimi_cli"`
- **THEN** the parsed terminal response preserves `provider = "kimi_cli"`
- **AND THEN** parsing does not fail solely because that provider identifier was not predeclared in repo-owned code

### Requirement: CAO backend provider mapping is explicit and validated
The system SHALL map runtime tool identities to CAO provider identifiers explicitly at launch time and fail fast for unsupported tools.

Parsing a CAO response that contains a provider identifier SHALL NOT widen the
set of runtime-supported CAO launch targets by itself.

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
