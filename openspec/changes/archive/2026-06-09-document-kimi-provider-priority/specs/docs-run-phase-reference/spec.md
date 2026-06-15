## ADDED Requirements

### Requirement: Run-phase references order Kimi before Gemini in provider lists

Run-phase reference pages SHALL present Kimi Code before Gemini in neutral provider lists while preserving backend-specific accuracy.

When run-phase docs list all maintained local-interactive tools, native headless backends, role-injection mappings, backend selection mappings, or relaunch continuation mappings, Kimi SHALL appear before Gemini unless the paragraph is specifically about Gemini behavior.

When run-phase diagrams or compact examples list only three providers, they SHALL include Claude, Codex, and Kimi.

Run-phase references that explain Kimi role injection SHALL warn that Kimi Code 0.11.0 does not expose a native system-prompt flag. The warning SHALL state that Kimi role delivery can rely on bootstrap or managed auto-skill workflows, and that Kimi users may need to invoke `houmao-auto-system-prompt` manually before substantive chat begins when automatic skill startup has not confirmed the prompt.

#### Scenario: Backend reference keeps Kimi visible in primary provider lists

- **WHEN** a reader opens `docs/reference/run-phase/backends.md`
- **THEN** neutral lists of maintained tools or provider mappings place Kimi before Gemini
- **AND THEN** Gemini-specific backend sections and validation checklists remain present and accurate

#### Scenario: Launch plan and role injection references use Kimi-priority ordering

- **WHEN** a reader opens launch-plan or role-injection run-phase references
- **THEN** provider lists and per-backend summary tables place Kimi before Gemini
- **AND THEN** backend-specific role-injection descriptions remain accurate for each provider

#### Scenario: Session lifecycle continuation mappings place Kimi before Gemini

- **WHEN** a reader opens the session lifecycle reference for provider-native relaunch mappings
- **THEN** Kimi Code appears before Gemini CLI in neutral mapping lists
- **AND THEN** Kimi-specific resume-conflict caveats remain documented

#### Scenario: Role-injection reference warns about Kimi native system-prompt gap

- **WHEN** a reader opens the Kimi role-injection or backend reference
- **THEN** the docs state that Kimi Code 0.11.0 lacks a native system-prompt flag
- **AND THEN** the docs state that `houmao-auto-system-prompt` may require manual invocation before substantive Kimi chat begins when automatic loading has not happened
