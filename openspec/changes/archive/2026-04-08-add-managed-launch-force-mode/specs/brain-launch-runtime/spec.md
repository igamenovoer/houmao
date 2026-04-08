## ADDED Requirements

### Requirement: Managed local force takeover replaces the live predecessor before replacement publication

When managed local launch resolves a fresh live predecessor for the target managed identity, the runtime SHALL treat force takeover as predecessor replacement rather than as direct shared-registry overwrite.

When no force mode is supplied, the runtime SHALL fail the launch rather than replacing that live predecessor.

When force takeover is supplied, the runtime SHALL resolve the predecessor by authoritative `agent_id` when the launch provides an explicit `agent_id`; otherwise it SHALL resolve by the managed identity selected for the current launch.

During force takeover, the runtime SHALL stop the resolved predecessor and make it stand down before the replacement session publishes its own fresh shared-registry record.

The runtime SHALL NOT choose a takeover target from tmux session name alone.

#### Scenario: Missing force leaves the predecessor in place
- **WHEN** a managed local launch resolves managed identity `worker-a`
- **AND WHEN** a fresh live predecessor already owns that same identity
- **AND WHEN** no force mode is supplied
- **THEN** the runtime fails the launch rather than replacing the predecessor

#### Scenario: Force takeover stops the predecessor before replacement publish
- **WHEN** a managed local launch resolves managed identity `worker-a`
- **AND WHEN** a fresh live predecessor already owns that same identity
- **AND WHEN** the launch supplies force mode `keep-stale`
- **THEN** the runtime stops that predecessor and waits for it to stand down
- **AND THEN** the replacement session publishes only after the predecessor has stood down

#### Scenario: Tmux session-name reuse alone does not determine the takeover target
- **WHEN** an unrelated live session already uses tmux session name `worker-a`
- **AND WHEN** a managed local launch resolves managed identity `worker-b`
- **AND WHEN** the launch supplies force mode `clean`
- **THEN** the runtime does not treat the unrelated tmux session as the predecessor for `worker-b`

### Requirement: Managed force modes define cleanup boundaries for replacement launch

When force mode is `keep-stale`, the runtime SHALL reuse the predecessor managed home in place and SHALL leave untouched stale runtime artifacts outside the newly written projection targets alone.

When force mode is `keep-stale`, the runtime SHALL NOT promise validation, cleanup, or repair of leftover stale artifacts that the replacement launch does not touch.

When force mode is `clean`, the runtime SHALL remove predecessor-owned replaceable launch artifacts before rebuilding, including the predecessor managed home and predecessor-owned session-local runtime artifacts that are safe to replace.

For both force modes, the runtime SHALL preserve arbitrary operator-owned paths and shared mailbox message stores that are not replacement-owned artifacts.

If replacement launch fails after predecessor stop or cleanup has already begun, the runtime SHALL surface that failure explicitly and SHALL NOT automatically restore the old predecessor session.

#### Scenario: `keep-stale` leaves untouched stale artifacts in place
- **WHEN** a predecessor managed home contains an unrelated stale file that the new build will not touch
- **AND WHEN** replacement launch uses force mode `keep-stale`
- **THEN** the runtime leaves that stale file in place
- **AND THEN** the runtime does not fail solely to clean or validate that untouched file

#### Scenario: `clean` removes predecessor-owned replaceable artifacts before rebuilding
- **WHEN** a predecessor session owns a managed home, session root, and job directory for managed identity `worker-a`
- **AND WHEN** replacement launch uses force mode `clean`
- **THEN** the runtime removes those predecessor-owned replaceable artifacts before rebuilding the replacement launch
- **AND THEN** the runtime does not delete unrelated operator-owned paths such as the runtime workdir

#### Scenario: Failed replacement does not resurrect the predecessor automatically
- **WHEN** replacement launch uses force mode `clean`
- **AND WHEN** predecessor cleanup has already started
- **AND WHEN** the replacement launch later fails
- **THEN** the runtime reports the replacement failure explicitly
- **AND THEN** it does not automatically restart or restore the old predecessor session
