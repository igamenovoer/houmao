## MODIFIED Requirements

### Requirement: `houmao-mgr agents launch` reports unattended strategy compatibility failures distinctly

When local `houmao-mgr agents launch` requests launch settings that must be resolved before provider startup, the command SHALL report launch-policy compatibility failures distinctly from backend-selection failures and post-start provider-runtime failures.

#### Scenario: Interactive-surface Claude launch reports unattended version gap before provider startup

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--headless`
- **AND WHEN** the selected preset resolves to unattended launch policy, whether explicitly through `launch.prompt_mode: unattended` or implicitly through the unattended default
- **AND WHEN** no compatible Claude strategy exists for the detected version on the local interactive launch surface
- **THEN** the command fails before Claude Code starts
- **AND THEN** the error identifies the requested unattended policy, detected Claude version, and local interactive launch surface
- **AND THEN** the error makes clear that launch-mode selection succeeded but provider startup was blocked before the tmux-attached TUI became ready

#### Scenario: Headless Claude launch reports unattended version gap before provider startup

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --headless`
- **AND WHEN** the selected preset resolves to unattended launch policy, whether explicitly through `launch.prompt_mode: unattended` or implicitly through the unattended default
- **AND WHEN** no compatible Claude strategy exists for the detected version on the `claude_headless` backend
- **THEN** the command fails before Claude Code starts
- **AND THEN** the error identifies the requested unattended policy, detected Claude version, and `claude_headless` backend
- **AND THEN** the error makes clear that launch-mode selection succeeded but provider startup was blocked before the detached headless runtime session became live

### Requirement: `houmao-mgr agents launch` preserves preset launch settings during local build

When `houmao-mgr agents launch` resolves a native preset-backed target from the canonical parsed catalog, it SHALL preserve the preset's requested launch settings when building the brain manifest for local startup.

At minimum, preset `launch.prompt_mode` and preset `launch.overrides` SHALL be forwarded into brain construction so the built manifest and subsequent runtime launch use the same requested launch posture and overrides.

For `launch.prompt_mode`, the effective preserved values SHALL use the `unattended|as_is` policy vocabulary, and preset omission SHALL resolve to unattended before manifest write.

#### Scenario: Omitted prompt mode defaults to unattended during local `agents launch`

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **AND WHEN** the selected preset omits `launch.prompt_mode`
- **THEN** the local brain build records unattended operator-prompt intent in the built brain manifest
- **AND THEN** the local runtime launch uses that unattended intent for the selected launch surface

#### Scenario: Explicit as-is policy survives local `agents launch`

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **AND WHEN** the selected preset requests `launch.prompt_mode: as_is`
- **THEN** the local brain build records `as_is` operator-prompt intent in the built brain manifest
- **AND THEN** the local runtime launch leaves provider startup behavior untouched for the selected launch surface

#### Scenario: Preset launch overrides survive local `agents launch`

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex`
- **AND WHEN** the selected preset requests `launch.overrides.tool_params`
- **THEN** the local brain build records the equivalent launch overrides in the built manifest
- **AND THEN** the local runtime launch uses those preserved overrides for the selected tool
