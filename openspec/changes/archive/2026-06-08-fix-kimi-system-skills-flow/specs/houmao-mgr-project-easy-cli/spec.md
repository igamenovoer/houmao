# houmao-mgr-project-easy-cli Specification

## ADDED Requirements

### Requirement: Kimi project agents launch through local interactive posture by default

`houmao-mgr project agents launch` SHALL treat Kimi specialists and Kimi-backed project profiles as maintained TUI/local-interactive launch candidates when the operator does not request headless posture.

When a selected specialist or selected project profile resolves to tool `kimi` and no direct or stored headless posture applies, the command SHALL delegate to the native managed-agent launch flow without rejecting the launch as headless-only.

When a selected specialist or selected project profile resolves to tool `kimi` and the operator explicitly passes `--headless`, the command SHALL preserve the explicit headless request and delegate to the maintained Kimi headless backend.

The existing Gemini headless-only rule SHALL remain unchanged. A Gemini-backed launch without `--headless` SHALL still fail clearly and identify Gemini as the required-headless exception.

#### Scenario: Kimi specialist launches without `--headless`

- **WHEN** a project specialist `kimi-reviewer` exists with tool `kimi`
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist kimi-reviewer --name kimi-reviewer-1` without `--headless`
- **THEN** the command delegates to native managed-agent launch for tool `kimi`
- **AND THEN** the launch resolves to TUI/local-interactive posture when no stronger stored posture requires headless
- **AND THEN** the command does not fail with a Gemini-and-Kimi headless-only error

#### Scenario: Kimi project profile launches without `--headless`

- **WHEN** project profile `kimi-reviewer-profile` targets a specialist whose tool is `kimi`
- **AND WHEN** the profile does not store headless posture
- **AND WHEN** an operator runs `houmao-mgr project agents launch --profile kimi-reviewer-profile`
- **THEN** the command delegates to native managed-agent launch for tool `kimi`
- **AND THEN** the launch resolves to TUI/local-interactive posture when no direct override requests headless

#### Scenario: Explicit Kimi headless launch remains supported

- **WHEN** a project specialist `kimi-reviewer` exists with tool `kimi`
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist kimi-reviewer --name kimi-reviewer-1 --headless`
- **THEN** the command preserves the explicit headless request
- **AND THEN** the delegated launch uses the maintained Kimi headless backend instead of local interactive TUI posture

#### Scenario: Gemini remains required-headless

- **WHEN** a project specialist `gemini-reviewer` exists with tool `gemini`
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist gemini-reviewer --name gemini-reviewer-1` without `--headless`
- **THEN** the command fails clearly before launch
- **AND THEN** it identifies Gemini as the project easy launch surface's required-headless provider
