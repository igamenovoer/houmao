## MODIFIED Requirements

### Requirement: The demo SHALL support Claude Code and Codex headless lanes through `project easy`
The supported demo SHALL expose three maintained lanes:

- Claude Code headless
- Codex headless
- Gemini headless

For each maintained lane, the demo SHALL:

- import or materialize the expected project-local auth bundle,
- create or reuse one specialist through `houmao-mgr project easy specialist create`,
- launch one headless instance through `houmao-mgr project easy instance launch --headless`.

The Gemini lane SHALL use the maintained Gemini headless contract already supported by project-local Gemini auth and easy-specialist flows, including API-key auth with optional `GOOGLE_GEMINI_BASE_URL` and OAuth auth via `oauth_creds.json`.

The demo SHALL persist the selected tool in canonical demo state rather than encoding it in a tool-specific output-root path.

The maintained demo contract SHALL follow supported unattended headless launch posture and SHALL NOT claim unsupported maintained lanes merely because a backend exists.

#### Scenario: Claude headless lane starts through project easy
- **WHEN** an operator runs the demo for tool `claude`
- **THEN** the demo creates or reuses a project-local Claude auth bundle under the redirected overlay
- **AND THEN** it creates or reuses a Claude specialist through `houmao-mgr project easy specialist create`
- **AND THEN** it launches one Claude headless instance through `houmao-mgr project easy instance launch --headless`
- **AND THEN** the selected tool is persisted in canonical demo state under the shared output root

#### Scenario: Codex headless lane starts through project easy
- **WHEN** an operator runs the demo for tool `codex`
- **THEN** the demo creates or reuses a project-local Codex auth bundle under the redirected overlay
- **AND THEN** it creates or reuses a Codex specialist through `houmao-mgr project easy specialist create`
- **AND THEN** it launches one Codex headless instance through `houmao-mgr project easy instance launch --headless`
- **AND THEN** the selected tool is persisted in canonical demo state under the shared output root

#### Scenario: Gemini headless lane starts through project easy
- **WHEN** an operator runs the demo for tool `gemini`
- **THEN** the demo creates or reuses a project-local Gemini auth bundle under the redirected overlay using one maintained Gemini auth family
- **AND THEN** it creates or reuses a Gemini specialist through `houmao-mgr project easy specialist create`
- **AND THEN** it launches one Gemini headless instance through `houmao-mgr project easy instance launch --headless`
- **AND THEN** the selected tool is persisted in canonical demo state under the shared output root
