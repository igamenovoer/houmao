# Spec Delta

## ADDED Requirements

### Requirement: Managed providers inherit the resolved owner launch environment

For Houmao-started Headless, Service, TUI, and Web providers, the native process SHALL receive the resolved owner baseline, declared launch env, and required runtime bindings. Native processes and their local shell and tool children SHALL receive the publishable settings. Ambient forwarding SHALL be limited to approved owner-side inputs.

#### Scenario: A Web provider executes a local shell command

- **WHEN** Houmao starts DSH Web or Kimi Web with a selected project context, a persistent feature flag, and a one-off diagnostic flag
- **THEN** the native Web process and a local shell it starts receive the resolved context and both flags

#### Scenario: An owner supplies ordinary environment settings

- **WHEN** an owner launches an agent with an approved baseline and supplies a non-secret setting through `--env-set NAME`
- **AND WHEN** the owner environment also contains an undeclared variable outside the baseline
- **THEN** the provider receives the declared owner-side value and omits the undeclared variable

### Requirement: Managed launch credentials use private inputs

The runtime SHALL deliver credentials and internal launch tokens through authorized owner-private inputs. Publishable env records SHALL reject assignments to runtime-owned names and selected credential bindings. Public runtime metadata, pane commands, and diagnostics SHALL exclude credential values.

#### Scenario: A provider needs a credential environment value

- **WHEN** a managed launch selects an auth bundle with an allowlisted credential value
- **THEN** the runtime delivers the value through the provider launch environment
- **AND THEN** the value is absent from the recorded pane command, public session manifest, registry, and Houmao diagnostics

#### Scenario: A declared environment assignment attempts to replace an owned binding

- **WHEN** an operator declares a publishable value for the manifest pointer, a Houmao-owned root selector, or a selected credential binding
- **THEN** the launch rejects the assignment and identifies the variable by name without printing its value

## MODIFIED Requirements

### Requirement: Tmux-backed sessions support session-local relaunch without rebuilding the brain home

For tmux-backed managed sessions, the system SHALL expose a relaunch surface that reuses the already-built agent home and does not route through build-time `houmao-mgr agents launch` behavior.

The public operator surface SHALL be `houmao-mgr agents relaunch`, and gateway-managed relaunch SHALL use the same internal runtime relaunch primitive rather than shelling out to the build-time launch command.

The persisted manifest SHALL carry secret-free `agent_launch_authority` describing the relaunch posture. Houmao-started sessions SHALL rebuild the provider environment from durable launch inputs. Joined sessions SHALL resolve explicit inherited env bindings through their adopted tmux launch contract.

Tmux-backed relaunch SHALL resolve the target session through the same manifest-first discovery contract used by current-session attach.

Tmux-backed relaunch SHALL always target tmux window `0` for the managed agent surface and SHALL NOT allocate a new tmux window.

The system SHALL NOT require per-agent launcher directories, copied launcher scripts, or copied credentials in shared registry in order to relaunch a tmux-backed managed session.

For native headless sessions, relaunch remains valid between turns even when no live `runtime.agent_pid` is published.

#### Scenario: Current-session relaunch uses tmux session env and existing built home
- **WHEN** a developer runs `houmao-mgr agents relaunch` inside a Houmao-started tmux-backed managed session
- **THEN** the system discovers the session through the `HOUMAO_MANIFEST_PATH` or `HOUMAO_AGENT_ID` locator published to tmux
- **AND THEN** it relaunches the managed agent surface from manifest-owned posture and durable launch inputs
- **AND THEN** it does not rebuild the brain home

#### Scenario: Gateway-managed relaunch shares the same runtime primitive
- **WHEN** an attached gateway requests relaunch for a tmux-backed managed session
- **THEN** the gateway uses the same manifest-backed runtime relaunch primitive as `houmao-mgr agents relaunch`
- **AND THEN** it does not fall back to build-time `houmao-mgr agents launch`

#### Scenario: Relaunch reuses window 0 rather than allocating a new window
- **WHEN** the runtime relaunches a tmux-backed managed session
- **THEN** it targets the managed agent surface in window `0`
- **AND THEN** it does not create or search for another tmux window when window `0` has been repurposed by the user

### Requirement: Relaunch preserves durable specialist env but not one-off instance-launch env

For Houmao-started tmux-backed sessions, relaunch SHALL rebuild provider-start state from durable persisted launch inputs, including when resuming an exact native chat. Persistent specialist env records SHALL be reapplied. `project agents launch --env-set` SHALL override ordinary settings for the current live generation only. One-off launch values SHALL stay out of specialist config, the built brain manifest, and session-manifest relaunch authority.

#### Scenario: Relaunch keeps persistent specialist env records
- **WHEN** a specialist declares persistent launch env record `FEATURE_FLAG_X=1`
- **AND WHEN** one tmux-backed session for that specialist is later relaunched
- **THEN** the relaunched session still uses `FEATURE_FLAG_X=1` from its durable launch input

#### Scenario: Relaunch drops one-off instance-launch env
- **WHEN** a tmux-backed session starts with `project agents launch --env-set FEATURE_FLAG_X=2`
- **AND WHEN** no durable launch input supplies `FEATURE_FLAG_X`
- **AND WHEN** that session is later relaunched
- **THEN** `FEATURE_FLAG_X` is absent from the relaunched provider environment and the owned tmux session environment

#### Scenario: Live-session headless turns can still use one-off instance-launch env before relaunch
- **WHEN** a headless tmux-backed session starts with one-off `project agents launch --env-set FEATURE_FLAG_X=2`
- **AND WHEN** the session remains live without relaunch
- **THEN** later runtime-controlled work in that same live session still uses `FEATURE_FLAG_X=2`
- **AND THEN** the value is absent from durable relaunch posture

#### Scenario: Exact chat relaunch restores the persistent value after an override
- **WHEN** a specialist declares `REVIEW_LEVEL=normal` and an instance starts with `--env-set REVIEW_LEVEL=verbose`
- **AND WHEN** the operator relaunches into the same native chat
- **THEN** both the relaunched provider and tmux session use `REVIEW_LEVEL=normal`

#### Scenario: Reattach keeps the current generation's one-off override
- **WHEN** a live generation uses `REVIEW_LEVEL=verbose` from one-off launch env
- **AND WHEN** a controller reattaches from an environment with a different value
- **THEN** the live generation continues to use `REVIEW_LEVEL=verbose`
