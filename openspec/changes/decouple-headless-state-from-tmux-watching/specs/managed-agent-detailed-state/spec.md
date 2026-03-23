## ADDED Requirements

### Requirement: Headless detailed state treats tmux liveness as auxiliary diagnostics
For managed headless agents, `GET /houmao/agents/{agent_ref}/state/detail` SHALL describe active-turn and last-turn posture from controller-owned execution state and durable turn records.

The headless detail payload MAY expose tmux liveness fields for inspectability or degradation reporting, but those tmux fields SHALL NOT by themselves redefine active-turn status, last-turn result, or the durability of a terminal turn outcome.

For managed headless agents, detail payloads SHALL surface the reconciled controller-owned terminal status even when execution evidence was missing or legacy metadata was insufficient; callers SHALL receive failed-with-diagnostic semantics rather than a tmux-driven `unknown` fallback.

#### Scenario: Detail preserves reconciled last-turn result when tmux session is gone
- **WHEN** a managed headless turn has already reconciled to a terminal failed or interrupted result
- **AND WHEN** the bound tmux session is no longer live
- **THEN** `GET /houmao/agents/{agent_ref}/state/detail` returns that reconciled last-turn result together with its execution evidence
- **AND THEN** tmux liveness appears only as additional diagnostic or inspectability posture

#### Scenario: Detail reports active headless turn from server-owned turn authority
- **WHEN** a managed headless agent currently has an accepted active turn
- **AND WHEN** no terminal execution evidence exists yet for that turn
- **THEN** `GET /houmao/agents/{agent_ref}/state/detail` reports that turn as active from server-owned turn authority
- **AND THEN** the caller does not need tmux watch semantics to determine that the agent is still busy

#### Scenario: Detail preserves failed-with-diagnostic status for degraded evidence
- **WHEN** a managed headless turn has already been reconciled to failed because execution evidence was missing or insufficient
- **AND WHEN** tmux liveness is absent or no longer inspectable
- **THEN** `GET /houmao/agents/{agent_ref}/state/detail` returns the failed terminal status together with available diagnostic context
- **AND THEN** the caller does not need to interpret a separate tmux-derived `unknown` state
