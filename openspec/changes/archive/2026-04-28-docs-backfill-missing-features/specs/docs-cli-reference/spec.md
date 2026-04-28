## ADDED Requirements

### Requirement: CLI reference documents degraded and stale recovery paths

The CLI reference SHALL document degraded and stale recovery behavior in the `agents stop` and `agents relaunch` command descriptions. The descriptions SHALL state that these commands probe the target tmux session before acting and route through recovery helpers when the session is degraded or stale. The descriptions SHALL link to the dedicated degraded-stale recovery reference page.

#### Scenario: Reader discovers recovery from CLI reference

- **WHEN** a reader reads the `agents stop` or `agents relaunch` CLI description
- **THEN** they see mention of the degraded/stale recovery path and a link to the dedicated recovery page

### Requirement: CLI reference documents cleanup purge-registry flag

The CLI reference SHALL document the `agents cleanup session --purge-registry` flag in the cleanup command family. The description SHALL explain that this flag deletes the lifecycle record entirely (rather than retiring it) and is intended for confirmed broken active local authority after tmux inspection.

#### Scenario: Reader understands purge-registry from CLI reference

- **WHEN** a reader reads the `agents cleanup session` CLI description
- **THEN** they see `--purge-registry` documented with its destructive semantics and the condition that it requires confirmed broken authority
