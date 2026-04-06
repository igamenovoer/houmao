## MODIFIED Requirements

### Requirement: The tracked demo assets use the canonical minimal agent-definition layout

The tracked minimal demo SHALL include only the secret-free files needed to explain the canonical preset-backed launch shape:
- `inputs/agents/skills/`
- `inputs/agents/roles/minimal-launch/system-prompt.md`
- `inputs/agents/presets/minimal-launch-claude-default.yaml`
- `inputs/agents/presets/minimal-launch-codex-default.yaml`
- `inputs/agents/tools/claude/adapter.yaml`
- `inputs/agents/tools/claude/setups/default/...`
- `inputs/agents/tools/codex/adapter.yaml`
- `inputs/agents/tools/codex/setups/default/...`

The tracked demo tree SHALL NOT commit plaintext auth contents under `inputs/agents/tools/<tool>/auth/`.

#### Scenario: Maintainer inspects the tracked demo tree
- **WHEN** a maintainer inspects `scripts/demo/minimal-agent-launch/inputs/agents/`
- **THEN** they find the canonical `skills/`, `roles/`, `presets/`, and `tools/` layout for one shared role with Claude and Codex presets
- **AND THEN** the tracked tree does not contain committed plaintext auth bundles

### Requirement: The demo launches the same role selector through either supported provider

The demo SHALL use one shared role selector, `minimal-launch`, and SHALL support launching that role through either `claude_code` or `codex` in headless mode via `houmao-mgr agents launch`.

#### Scenario: Claude headless demo run succeeds through the shared role selector
- **WHEN** an operator runs the supported demo for provider `claude_code`
- **THEN** the demo launches `houmao-mgr agents launch` using selector `minimal-launch`
- **AND THEN** the resolved preset comes from `presets/minimal-launch-claude-default.yaml`
- **AND THEN** the launch runs in headless mode

#### Scenario: Codex headless demo run succeeds through the shared role selector
- **WHEN** an operator runs the supported demo for provider `codex`
- **THEN** the demo launches `houmao-mgr agents launch` using selector `minimal-launch`
- **AND THEN** the resolved preset comes from `presets/minimal-launch-codex-default.yaml`
- **AND THEN** the launch runs in headless mode
