# Spec Delta

## ADDED Requirements

### Requirement: Agent inspect skill covers durable usage records, service/web endpoints, external agents, and state fields
`houmao-agent-inspect` SHALL cover durable usage inspection (`GET /v1/usage`, `GET /houmao/agents/{agent_ref}/usage`, `<session-root>/usage/records.sqlite3`, `usage-start.json`, `usage-final.json`), `service` state/request endpoints (`/v1/control/service/state`, `/v1/control/service/requests/{request_id}`) and `web` state/history endpoints (`/v1/control/web/state`, `/v1/control/web/history`), `agents external list|get`, and `state` gateway policy/default-group/`execution_binding` fields.

#### Scenario: Operator or agent inspects turn usage, service state, or external agent state
- **WHEN** a caller inspects turn token/cost accounting, a `service` or `web` agent, or an `agents external` import
- **THEN** `commands/discover.md`, `commands/logs.md`, and `commands/artifacts.md` cover `/v1/usage` pagination, `usage-*.json`, `/v1/control/service/{state,requests/{request_id}}`, `/v1/control/web/{state,history}`, `agents external list|get`, and `execution_binding`

### Requirement: Agent inspect skill strips cross-skill boilerplate from SKILL-MAIN.md
`houmao-agent-inspect/SKILL-MAIN.md` SHALL remove duplicated launcher, Missing-Input, `houmao-cli`, and redundant Supported/Out-of-Scope/Routing lists into a lean ~85-line entrypoint per `imsight-agent-skill-handling`.

#### Scenario: Inspect entrypoint matches concise subskill pattern
- **WHEN** a reviewer inspects `houmao-agent-inspect/SKILL-MAIN.md`
- **THEN** it keeps concise `## Workflow`, `## Actor Frame Gate`, `## Subcommands` table (`help`, `discover`, `screen`, `mailbox`, `artifacts`, `logs`), and skill-specific `DO NOT ...` guardrails

### Requirement: Agent inspect skill preserves read-only boundary, managed-first hierarchy, and socket-qualified tmux
`houmao-agent-inspect` SHALL preserve `## Actor Frame Gate`, strictly read-only inspection, managed-observation preference over raw tmux, verified socket-qualified tmux capture (`env -u TMUX -u TMUX_PANE tmux -S "$TMUX_SOCKET" -N capture-pane`), and never auto-invoking terminal recording unless explicitly asked.

#### Scenario: Screen inspection uses recorded tmux socket without ambient tmux leakage
- **WHEN** managed endpoints do not suffice and `houmao-agent-inspect->screen()` inspects a local tmux pane
- **THEN** it reads the recorded socket with `env -u TMUX -u TMUX_PANE tmux -S "$TMUX_SOCKET" -N capture-pane` and never guesses ambient tmux servers or starts a terminal recorder unasked
