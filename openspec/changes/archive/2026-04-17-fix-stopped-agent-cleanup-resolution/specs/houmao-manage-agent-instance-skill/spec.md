## ADDED Requirements

### Requirement: `houmao-agent-instance` cleanup guidance prefers durable post-stop locators
The packaged `houmao-agent-instance` cleanup guidance SHALL tell agents to use durable cleanup locators from stop output when cleaning artifacts after a stop action.

When recent stop output includes `manifest_path` or `session_root`, the guidance SHALL prefer `houmao-mgr agents cleanup session|logs --manifest-path <path>` or `--session-root <path>` over `--agent-id` or `--agent-name`.

When no durable path locator is available but the user provides a concrete `agent_id` or `agent_name`, the guidance MAY route cleanup through `--agent-id` or `--agent-name` and SHALL describe that selector cleanup can recover stopped sessions through bounded runtime-root fallback after live registry removal.

The guidance SHALL NOT instruct agents to create, search, or depend on stopped-session tombstones, stopped-agent indexes, or additional shared-registry state.

#### Scenario: Cleanup after stop uses manifest path from stop output
- **WHEN** an agent has recent stop output that includes `manifest_path = "/repo/.houmao/runtime/sessions/local_interactive/session-1/manifest.json"`
- **AND WHEN** the user asks to clean the stopped session envelope
- **THEN** the skill guidance directs the agent to use `houmao-mgr agents cleanup session --manifest-path /repo/.houmao/runtime/sessions/local_interactive/session-1/manifest.json`
- **AND THEN** it does not prefer a registry-only `--agent-name` selector for that post-stop cleanup

#### Scenario: Cleanup without path locator may use name or id fallback
- **WHEN** the user asks to clean stopped-session logs for managed agent `reviewer`
- **AND WHEN** recent context does not include a `manifest_path` or `session_root`
- **THEN** the skill guidance may direct the agent to use `houmao-mgr agents cleanup logs --agent-name reviewer`
- **AND THEN** the guidance acknowledges that stopped-session selector cleanup depends on runtime-root fallback if the live registry record has already been removed

#### Scenario: Cleanup guidance does not invent tombstones
- **WHEN** an agent follows `houmao-agent-instance` cleanup guidance for a stopped session
- **THEN** the guidance does not tell the agent to create or search a stopped-session tombstone or stopped-agent index
- **AND THEN** it stays within supported `houmao-mgr agents cleanup session|logs` selectors
