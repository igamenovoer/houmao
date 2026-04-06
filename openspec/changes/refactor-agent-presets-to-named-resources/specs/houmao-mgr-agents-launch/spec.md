## MODIFIED Requirements

### Requirement: `houmao-mgr agents launch` resolves preset selectors with explicit default-setup behavior

`houmao-mgr agents launch` SHALL support exactly two preset selector forms on `--agents`:

- bare role selector `<role>`, resolved together with the provider-derived tool to the unique named preset whose `role=<role>`, `tool=<tool>`, and `setup=default`
- explicit preset file path

The command SHALL NOT interpret `<role>/<setup>` as selector shorthand in this change.

#### Scenario: Bare role selector resolves the default setup through a named preset
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **THEN** the command SHALL resolve the unique preset whose content declares `role: gpu-kernel-coder`, `tool: claude`, and `setup: default`
- **AND THEN** the resolved preset file SHALL live under `agents/presets/`

#### Scenario: Explicit preset path selects a non-default setup
- **WHEN** an operator runs `houmao-mgr agents launch --agents agents/presets/gpu-kernel-coder-codex-yunwu-openai.yaml --provider codex`
- **THEN** the command SHALL resolve that explicit preset file path directly

#### Scenario: Hybrid role-setup shorthand is rejected
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder/research --provider claude_code`
- **THEN** the command SHALL NOT reinterpret that selector as `<role>/<setup>`
- **AND THEN** it SHALL fail clearly unless that input resolves as an explicit preset file path
