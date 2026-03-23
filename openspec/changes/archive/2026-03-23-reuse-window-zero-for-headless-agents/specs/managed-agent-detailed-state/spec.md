## ADDED Requirements

### Requirement: Headless detailed state anchors tmux inspectability to the stable primary surface
For managed headless agents, the detailed state payload SHALL keep any tmux inspectability metadata anchored to the stable primary agent surface.

When such inspectability metadata is exposed, it SHALL anchor that metadata to the stable primary agent surface in window 0 rather than to transient per-turn windows.

When that metadata includes a window name, it SHALL use the stable value `agent` for managed-headless sessions created under this contract.

Auxiliary tmux windows MAY exist in the same session, but the detailed state payload SHALL NOT imply that active-turn identity, last-turn identity, or operator attach guidance depends on those auxiliary windows.

#### Scenario: Detailed state keeps attach guidance on the primary agent surface
- **WHEN** a caller requests detailed state for a managed headless agent that is currently active
- **THEN** any tmux-facing inspectability information in that payload refers to the stable primary agent surface in window 0
- **AND THEN** the caller does not need to discover a transient per-turn tmux window in order to watch the active agent output

#### Scenario: Auxiliary windows do not change detailed-state tmux guidance
- **WHEN** a managed headless session contains both its stable agent window and one or more auxiliary windows
- **THEN** the detailed state payload continues anchoring tmux inspectability to the stable primary agent surface
- **AND THEN** active-turn and last-turn posture remain controller-owned rather than inferred from auxiliary window topology

#### Scenario: Detailed state keeps stable window naming without adding a new attach-target field
- **WHEN** a caller requests detailed state for a managed headless agent created under this contract
- **THEN** any exposed tmux window metadata uses the stable name `agent`
- **AND THEN** the payload does not require a separate new attach-target field in order to describe the stable primary surface
