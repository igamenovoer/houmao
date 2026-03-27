## MODIFIED Requirements

### Requirement: Live demo scripts prove end-to-end prompt processing with real providers
In addition to unit tests, the repo SHALL include opt-in demo tutorial packs under `scripts/demo/<purpose-slug>/...` that demonstrate launching sessions and processing prompts end-to-end against real cloud providers using local auth bundles under `agents/tools/<tool>/auth/`.

Each demo SHALL follow the tutorial-pack guidance in `magic-context/instructions/explain/make-api-tutorial-pack.md` (step-by-step README, one-click `run_demo.sh`, temporary workspace, tracked minimal inputs, and a verification story via `expected_report/` + sanitizer or an explicit verifier).

#### Scenario: Codex CAO demo launches and returns a real response
- **WHEN** a developer runs the Codex CAO demo script with valid Codex/OpenAI credentials present under `agents/tools/codex/auth/`
- **AND WHEN** `cao-server` is running locally
- **THEN** the demo launches a CAO-backed Codex session, sends a prompt, and receives a non-empty model response

#### Scenario: Claude Code CAO demo launches and returns a real response
- **WHEN** a developer runs the Claude Code CAO demo script with valid Claude/Anthropic credentials present under `agents/tools/claude/auth/`
- **AND WHEN** `cao-server` is running locally
- **THEN** the demo launches a CAO-backed Claude Code session, sends a prompt, and receives a non-empty model response

#### Scenario: Gemini demo launches and returns a real response
- **WHEN** a developer runs the Gemini demo script with valid Gemini credentials present under `agents/tools/gemini/auth/`
- **THEN** the demo launches a Gemini session (using the runtime’s supported non-CAO backend) and receives a non-empty model response

#### Scenario: Demo tutorial pack has the required structure
- **WHEN** a developer inspects a demo under `scripts/demo/<purpose-slug>/`
- **THEN** it includes a `README.md` and a `run_demo.sh`
- **AND THEN** it uses a temporary workspace under `tmp/` (or another gitignored path)

#### Scenario: Missing credentials causes a demo to skip
- **WHEN** a developer runs an individual demo script
- **AND WHEN** the required auth bundle files under `agents/tools/<tool>/auth/` are missing
- **THEN** the demo reports SKIP with an actionable reason
- **AND THEN** the demo exits successfully without attempting provider calls

#### Scenario: Invalid credentials causes a demo to skip
- **WHEN** a developer runs an individual demo script
- **AND WHEN** the provider rejects the request due to invalid or unauthorized credentials from the selected auth bundle
- **THEN** the demo reports SKIP with the provider-facing failure reason
- **AND THEN** the demo exits successfully after preserving any sanitized diagnostic output it owns
