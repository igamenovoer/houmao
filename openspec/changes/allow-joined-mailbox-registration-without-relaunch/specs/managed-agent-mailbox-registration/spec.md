## MODIFIED Requirements

### Requirement: Late mailbox registration reports activation state by runtime posture
Late mailbox registration SHALL report activation state based on whether the target runtime posture becomes live-mailbox-actionable after the mutation, rather than claiming that every successful registration is immediately usable by the live provider process.

The supported activation outcomes SHALL include:

- `active`
- `pending_relaunch`

Headless local managed sessions SHALL report `active`.
Tmux-backed local interactive managed sessions SHALL report `active` when the runtime refreshes the owning tmux live mailbox projection successfully.
Joined tmux-backed managed sessions SHALL follow the same activation rule even when their relaunch posture is unavailable.
The runtime SHALL NOT fail late mailbox registration or unregistration solely because a joined tmux session lacks relaunch posture when the runtime can still update both the durable mailbox state and the owning tmux live mailbox projection safely.
The runtime SHALL report `pending_relaunch` only when the resulting mailbox binding is persisted durably but the current live session posture is not yet live-mailbox-actionable.

#### Scenario: Interactive local managed session becomes active after tmux live projection refresh
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** `alice` resolves to a tmux-backed local interactive managed session whose owning tmux session is reachable
- **THEN** the command persists the mailbox binding successfully
- **AND THEN** it refreshes the owning tmux live mailbox projection for that binding
- **AND THEN** the command reports activation state `active`

#### Scenario: Joined session without relaunch posture becomes active after registration
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** `alice` resolves to a joined tmux-backed managed session whose relaunch posture is unavailable
- **AND WHEN** the runtime can still update the session manifest and the owning tmux session environment for `alice`
- **THEN** the command persists the mailbox binding successfully
- **AND THEN** it refreshes the owning tmux live mailbox projection for that binding
- **AND THEN** the command reports activation state `active`

### Requirement: `houmao-mgr agents mailbox status` reports late mailbox registration posture
`houmao-mgr agents mailbox status` SHALL report whether an existing local managed agent currently has a late mailbox registration and whether that registration is active for runtime-owned mailbox use.

At minimum, the status output SHALL distinguish:

- no mailbox registration,
- an active filesystem mailbox registration,
- a persisted mailbox registration whose live mailbox projection is not yet current.

#### Scenario: Status reports active for a joined session after late registration
- **WHEN** an operator runs `houmao-mgr agents mailbox status --agent-name alice`
- **AND WHEN** `alice` has a persisted mailbox binding on a joined tmux-backed managed session
- **AND WHEN** the owning tmux session environment publishes the current mailbox projection for that binding
- **THEN** the command reports the persisted mailbox identity
- **AND THEN** the command reports activation state `active`
