## ADDED Requirements

### Requirement: Gateway operational docs explain outside-tmux tmux-session targeting
The gateway operational documentation SHALL explain when operators should use `--target-tmux-session` instead of `--current-session` or explicit managed-agent selectors.

That guidance SHALL explain that tmux-session targeting is resolved locally from the addressed tmux session's manifest-backed authority, with fresh shared-registry `terminal.session_name` fallback when the tmux-published manifest pointer is missing or stale.

The operational docs SHALL also explain that tmux-session targeting is a local host workflow and does not make tmux session names part of the remote managed-agent API contract.

When the docs describe explicit pair-managed targeting, they SHALL use the name `--pair-port` for the Houmao pair-authority override and SHALL distinguish that selector from gateway listener port overrides such as lower-level `--gateway-port`.

#### Scenario: Reader can choose between current-session and tmux-session targeting
- **WHEN** a reader needs to attach a gateway from a normal shell outside the owning tmux session
- **THEN** the gateway operations docs explain that `--target-tmux-session` is the correct selector for that workflow
- **AND THEN** the docs explain that `--current-session` remains the inside-tmux same-session path

#### Scenario: Reader understands tmux-session targeting authority and limits
- **WHEN** a reader needs to understand how `--target-tmux-session` finds the target session
- **THEN** the gateway operations docs explain the manifest-first resolution path with shared-registry tmux-alias fallback
- **AND THEN** the docs explain that tmux session names stay local CLI authority hints rather than remote API identifiers

#### Scenario: Reader can distinguish pair-authority port selection from gateway listener port selection
- **WHEN** a reader needs to target an explicit pair-managed authority while using gateway commands
- **THEN** the gateway operations docs explain that `--pair-port` selects the Houmao pair authority
- **AND THEN** the docs explain that gateway listener port overrides belong to lower-level gateway attach surfaces rather than `houmao-mgr agents gateway ...`
