# Spec Delta

## ADDED Requirements

### Requirement: Headless wakeup demo launches its maintained project lanes

The demo SHALL select a supported Claude or Codex lane, prepare its project-local auth and specialist, and launch exactly one agent through `houmao-mgr project agents launch --mode headless`. It SHALL record the selected tool in the canonical demo state and follow the existing unattended and scoped cleanup contracts.

#### Scenario: A Claude or Codex lane starts

- **WHEN** an operator starts the demo with either supported tool
- **THEN** the demo resolves its project auth, creates or reuses the specialist, launches the selected one-shot agent, and records the tool in the common run state

#### Scenario: An unsupported lane is requested

- **WHEN** the operator supplies a tool outside the maintained demo pair
- **THEN** the demo fails before importing credentials or starting a specialist

## REMOVED Requirements

### Requirement: The demo SHALL support Claude Code and Codex headless lanes through `project`

**Reason**: The manager now selects the native one-shot mode explicitly, and this demo's maintained provider set already excludes Gemini.

**Migration**: Run the project's Claude or Codex specialist with `--mode headless`.
