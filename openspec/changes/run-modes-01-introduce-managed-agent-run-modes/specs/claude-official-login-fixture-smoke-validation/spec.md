# Spec Delta

## MODIFIED Requirements

### Requirement: Repository provides a reproducible `official-login` Claude smoke launch flow

The smoke SHALL create a fresh external private workdir/project overlay, seed the `server-api-smoke` role, import the selected local vendor bundle through maintained credential behavior, and create a temporary specialist. It SHALL launch through `houmao-mgr project agents launch --mode headless` with unattended posture and use scoped agent stop/cleanup. It SHALL preserve native routing and require no state template.

#### Scenario: Smoke flow launches from a fresh temp workdir with a temporary project overlay
- **WHEN** a maintainer runs the vendor-login smoke with a selected imported bundle
- **THEN** it creates a fresh workdir and project overlay under the external private run root
- **AND THEN** prompt material comes from `tests/fixtures/plain-agent-def/roles/server-api-smoke/system-prompt.md`
- **AND THEN** it imports the selected bundle into that project and launches its specialist through the maintained project headless command

#### Scenario: Smoke flow proves projected vendor login-state works without a state template
- **WHEN** the selected imported bundle contains `.credentials.json` and valid minimized companion state
- **AND WHEN** the smoke launches from its fresh private project
- **THEN** the isolated Claude home uses the projected vendor login state without `claude_state.template.json`
- **AND THEN** neither DeepSeek routing nor unrelated ambient provider credentials are injected

#### Scenario: Smoke flow uses scoped selected-agent cleanup
- **WHEN** the smoke has captured the launched agent ID
- **THEN** it stops that agent with `houmao-mgr agents single --agent-id <agent_id> stop`
- **AND THEN** any session cleanup uses `houmao-mgr agents single --agent-id <agent_id> cleanup session`
- **AND THEN** it does not call retired root-level launch, stop, or cleanup commands
