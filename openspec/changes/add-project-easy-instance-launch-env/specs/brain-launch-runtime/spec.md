## ADDED Requirements

### Requirement: Relaunch preserves durable specialist env but not one-off instance-launch env

For Houmao-started tmux-backed sessions, relaunch SHALL rebuild provider-start state from durable persisted launch inputs rather than from one-off extra env supplied only at initial instance launch.

When the built brain manifest contains persistent specialist-owned launch env records, relaunch SHALL reapply those env records as part of the rebuilt launch plan.

When the original live session also received one-off extra env through `project easy instance launch --env-set`, that one-off extra env SHALL apply only to the current live session and SHALL NOT be persisted in relaunch authority.

The runtime SHALL NOT store one-off instance-launch extra env in:

- specialist config,
- the built brain manifest, or
- session-manifest relaunch authority.

#### Scenario: Relaunch keeps persistent specialist env records
- **WHEN** a specialist declares persistent launch env record `FEATURE_FLAG_X=1`
- **AND WHEN** one tmux-backed session for that specialist is later relaunched
- **THEN** the relaunched session still uses `FEATURE_FLAG_X=1`
- **AND THEN** the runtime obtains that value from durable specialist launch input rather than from the old live session's one-off launch state

#### Scenario: Relaunch drops one-off instance-launch env
- **WHEN** a tmux-backed session originally started with one-off `project easy instance launch --env-set FEATURE_FLAG_X=2`
- **AND WHEN** the underlying specialist does not declare persistent env record `FEATURE_FLAG_X`
- **AND WHEN** that session is later relaunched
- **THEN** the relaunched session does not keep `FEATURE_FLAG_X=2`
- **AND THEN** relaunch uses only durable launch input that was persisted before runtime rebuild

#### Scenario: Live-session headless turns can still use one-off instance-launch env before relaunch
- **WHEN** a headless tmux-backed session starts with one-off `project easy instance launch --env-set FEATURE_FLAG_X=2`
- **AND WHEN** the session remains live without relaunch
- **THEN** later runtime-controlled work in that same live session still uses `FEATURE_FLAG_X=2`
- **AND THEN** that behavior does not imply that `FEATURE_FLAG_X=2` is durable relaunch posture
