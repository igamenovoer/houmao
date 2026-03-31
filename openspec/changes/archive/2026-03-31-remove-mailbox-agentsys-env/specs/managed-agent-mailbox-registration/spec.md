## MODIFIED Requirements

### Requirement: Late mailbox registration reports activation state by runtime posture
Late mailbox registration SHALL report activation state based on whether the target runtime posture becomes actionable for runtime-owned mailbox work after the durable mailbox mutation, rather than on whether mailbox-specific tmux env projection was refreshed.

The supported activation outcomes for successful late mailbox registration or unregistration SHALL include:

- `active`

Headless local managed sessions SHALL report `active`.
Tmux-backed local interactive managed sessions SHALL report `active` when the runtime persists the mailbox binding and transport-specific validation succeeds for current mailbox work.
Joined tmux-backed managed sessions SHALL follow the same activation rule even when their relaunch posture is unavailable.
The runtime SHALL NOT fail late mailbox registration or unregistration solely because a joined tmux session lacks relaunch posture when the runtime can still update durable mailbox state and validate the resulting mailbox binding for current mailbox work.
If a requested mailbox mutation would leave the resulting durable mailbox binding non-actionable for runtime-owned mailbox work, the mutation SHALL fail explicitly rather than reporting `pending_relaunch`.

#### Scenario: Interactive local managed session becomes active after durable binding validation
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** `alice` resolves to a tmux-backed local interactive managed session whose durable mailbox binding can be validated for current mailbox work
- **THEN** the command persists the mailbox binding successfully
- **AND THEN** the command reports activation state `active`

#### Scenario: Joined session without relaunch posture becomes active after registration
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** `alice` resolves to a joined tmux-backed managed session whose relaunch posture is unavailable
- **AND WHEN** the runtime can still update the session manifest and validate the resulting mailbox binding for `alice`
- **THEN** the command persists the mailbox binding successfully
- **AND THEN** the command reports activation state `active`

### Requirement: `houmao-mgr agents mailbox status` reports late mailbox registration posture
`houmao-mgr agents mailbox status` SHALL report whether an existing local managed agent currently has a late mailbox registration and whether that registration is actionable for runtime-owned mailbox use.

At minimum, the status output SHALL distinguish:

- no mailbox registration,
- an active filesystem mailbox registration.

The command SHALL NOT report `pending_relaunch` as a mailbox activation outcome.

#### Scenario: Status reports no registration when the session is not mailbox-enabled
- **WHEN** an operator runs `houmao-mgr agents mailbox status --agent-name alice`
- **AND WHEN** `alice` has no persisted mailbox binding
- **THEN** the command reports that no mailbox registration is present
- **AND THEN** it does not report an activation state implying actionable mailbox support

#### Scenario: Status reports active for a joined session after late registration
- **WHEN** an operator runs `houmao-mgr agents mailbox status --agent-name alice`
- **AND WHEN** `alice` has a persisted mailbox binding on a joined tmux-backed managed session
- **AND WHEN** that binding validates as actionable for current mailbox work
- **THEN** the command reports the persisted mailbox identity
- **AND THEN** the command reports activation state `active`
