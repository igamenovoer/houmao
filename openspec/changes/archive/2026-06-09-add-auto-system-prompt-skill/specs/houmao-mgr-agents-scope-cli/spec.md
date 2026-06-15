## ADDED Requirements

### Requirement: Agents self exposes effective system prompt retrieval
`houmao-mgr agents self` SHALL expose a read-only `system-prompt show` command for the current managed agent.

`houmao-mgr agents self system-prompt show --format text` SHALL resolve the caller's current managed-agent identity through current-session authority and print the effective Houmao system prompt for that agent.

The command SHALL NOT accept `--agent-id`, `--agent-name`, or another explicit selector under `agents self`.

The command SHALL fail clearly outside a tmux/session context that resolves to a registered local managed-agent runtime identity.

#### Scenario: Managed agent reads its own system prompt
- **WHEN** a managed agent runs `houmao-mgr agents self system-prompt show --format text` inside its own registered session
- **THEN** the command resolves the current managed-agent identity without an explicit selector
- **AND THEN** it prints the effective Houmao system prompt for that managed agent

#### Scenario: Self system prompt rejects explicit selector
- **WHEN** an operator runs `houmao-mgr agents self system-prompt show --agent-name worker --format text`
- **THEN** the command fails because `agents self` targets only the current managed session
- **AND THEN** the diagnostic directs selected-agent inspection to a selected-agent command surface if one is maintained

#### Scenario: Self system prompt fails outside managed session
- **WHEN** an operator runs `houmao-mgr agents self system-prompt show --format text` outside a registered managed-agent session
- **THEN** the command fails clearly
- **AND THEN** the diagnostic explains that current-session managed-agent identity is required

### Requirement: Self system prompt command is safe for auto-skill use
The self system-prompt command SHALL be read-only and SHALL NOT mutate agent memory, mailbox state, gateway state, lifecycle state, or runtime manifests.

The command output SHALL contain the effective prompt text in text format without requiring the caller to know manifest paths, memory paths, launch-profile paths, or runtime overlay layout.

#### Scenario: Auto skill retrieves prompt without internal paths
- **WHEN** `houmao-auto-system-prompt` runs `houmao-mgr agents self system-prompt show --format text`
- **THEN** the command returns the effective prompt text through the supported CLI
- **AND THEN** the skill does not need to inspect runtime manifests or `houmao-memo.md`
