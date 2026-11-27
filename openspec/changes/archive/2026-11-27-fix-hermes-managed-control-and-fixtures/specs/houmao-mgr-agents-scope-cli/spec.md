# Spec Delta

## MODIFIED Requirements

### Requirement: Agents self scope operates on the verified current managed runtime
`houmao-mgr agents self` SHALL expose maintained operations whose target is the caller's single verified local managed agent.

At minimum, `agents self` SHALL expose:

- `identity`
- `state`
- `prompt`
- `interrupt`
- `relaunch`
- `gateway`
- `mail`
- `mailbox`
- `memory`
- `turn`

`agents self` SHALL require a verified current identity established through a supported Houmao launch.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Commands that act on a terminal SHALL verify the owning tmux session. Supported headless self commands SHALL accept their verified runtime-owned manifest locator without tmux. Hermes service and TUI self commands that use native runtime authority SHALL accept verified detached daemon callers.

`agents self` commands SHALL NOT accept `--agent-id`, `--agent-name`, or `--current-session` because the target is the current managed-agent identity by definition.

`agents self prompt` and `agents self interrupt` SHALL use the supported control path for the current managed session without accepting explicit agent selectors.

`agents self relaunch` SHALL refresh the active tmux-backed surface for the caller's current managed session. It SHALL require resolvable current-session manifest authority. It SHALL NOT perform selected-agent registry lookup, stopped relaunchable-record revival, degraded/stale active-record recovery, or cross-session targeting.

`agents self` SHALL NOT expose selected-agent lifecycle controls that terminate or clean up the caller's own tmux-backed runtime. In particular, `agents self stop` and `agents self cleanup` SHALL NOT be maintained public paths.

#### Scenario: Self identity requires an existing managed runtime
- **WHEN** an operator runs `houmao-mgr agents self identity` inside a manually started tmux session that lacks verified managed launch authority
- **THEN** the command fails and explains that a verified managed runtime is required
- **AND THEN** it leaves the manual process and its files untouched

#### Scenario: Self command resolves current tmux identity
- **WHEN** an agent runs `houmao-mgr agents self identity` inside its own registered managed tmux session
- **THEN** the command locates the runtime manifest through the current session and verifies it
- **AND THEN** the output reports the manifest's identity without requiring `--agent-id` or `--agent-name`

#### Scenario: Self relaunch refreshes active current session
- **WHEN** an agent runs `houmao-mgr agents self relaunch` inside its own registered managed tmux session
- **THEN** the command resolves current-session manifest authority
- **AND THEN** it refreshes the active tmux-backed primary surface for that current managed session
- **AND THEN** it does not perform selected-agent stopped-record revival or degraded/stale registry recovery

#### Scenario: Self command fails outside managed session
- **WHEN** an operator runs `houmao-mgr agents self mail status` with no verified current managed runtime
- **THEN** the command fails clearly
- **AND THEN** the diagnostic explains what owning session or runtime-owned context is required

#### Scenario: Self scope omits destructive lifecycle controls
- **WHEN** an operator runs `houmao-mgr agents self --help`
- **THEN** the help output lists current-session `prompt`, `interrupt`, and `relaunch`
- **AND THEN** it omits manual adoption and destructive lifecycle commands `stop` and `cleanup`
- **AND THEN** the documentation directs selected-agent stopped/degraded relaunch recovery, stop, and cleanup to `houmao-mgr agents single --agent-id <id> ...` or `houmao-mgr agents single --agent-name <name> ...`

#### Scenario: A Detached Hermes Tool Uses the Self Scope

- **WHEN** a current managed Hermes service or TUI tool invokes `agents self identity`, `agents self state`, or a supported self mail command outside tmux
- **THEN** the command targets the verified current managed runtime without accepting an explicit agent selector
- **AND THEN** terminal-specific operations continue to require their own supported authority
