## ADDED Requirements

### Requirement: `houmao-mgr agents launch` reports unattended strategy compatibility failures distinctly
When local `houmao-mgr agents launch` requests a launch policy that must be resolved before provider startup, the command SHALL report launch-policy compatibility failures distinctly from backend-selection failures and post-start provider-runtime failures.

#### Scenario: Interactive Claude launch reports unattended version gap before provider startup
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--headless`
- **AND WHEN** the selected recipe requests `launch_policy.operator_prompt_mode: unattended`
- **AND WHEN** no compatible Claude strategy exists for the detected version on the local interactive launch surface
- **THEN** the command fails before Claude Code starts
- **AND THEN** the error identifies the requested unattended policy, detected Claude version, and local interactive launch surface
- **AND THEN** the error makes clear that launch-mode selection succeeded but provider startup was blocked before the tmux-attached TUI became ready

#### Scenario: Headless Claude launch reports unattended version gap before provider startup
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --headless`
- **AND WHEN** the selected recipe requests `launch_policy.operator_prompt_mode: unattended`
- **AND WHEN** no compatible Claude strategy exists for the detected version on the `claude_headless` backend
- **THEN** the command fails before Claude Code starts
- **AND THEN** the error identifies the requested unattended policy, detected Claude version, and `claude_headless` backend
- **AND THEN** the error makes clear that launch-mode selection succeeded but provider startup was blocked before the detached headless runtime session became live
