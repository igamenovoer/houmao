## ADDED Requirements

### Requirement: Managed launch establishes primary tmux surface independent of user base indexes
`houmao-mgr agents launch` SHALL start Houmao-owned tmux-backed managed-agent sessions successfully when the user's tmux configuration sets non-zero default window or pane base indexes, provided tmux otherwise supports creating and moving the session's bootstrap surface.

For launched tmux-backed sessions, the command SHALL publish managed-agent metadata only after the runtime has established the contractual primary window index `0` and captured the primary tmux object handles needed for later operations.

If the primary surface cannot be established, launch SHALL fail before publishing an active shared-registry record for the attempted managed agent.

#### Scenario: Launch succeeds with one-based tmux indexes
- **WHEN** an operator's tmux configuration sets `base-index 1` and `pane-base-index 1`
- **AND WHEN** the operator runs `houmao-mgr agents launch` for a local tmux-backed provider
- **THEN** the launched managed-agent session owns primary window index `0`
- **AND THEN** the manifest records primary tmux object handles for the managed-agent surface
- **AND THEN** later prompt, capture, interrupt, gateway, and relaunch operations can target that primary surface without relying on `session:0.0`

#### Scenario: Failed primary-surface preparation does not publish active launch metadata
- **WHEN** `houmao-mgr agents launch` creates a tmux session but cannot establish the managed-agent primary window at index `0`
- **THEN** the command reports launch failure
- **AND THEN** it does not publish an active lifecycle-aware managed-agent registry record for that failed launch
