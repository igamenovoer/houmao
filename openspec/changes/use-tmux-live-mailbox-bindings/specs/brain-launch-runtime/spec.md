## ADDED Requirements

### Requirement: Tmux-backed sessions publish live-refreshable mailbox bindings into tmux session environment
For tmux-backed managed sessions, the runtime SHALL treat the targeted mailbox env vars published in tmux session environment as the live mailbox projection for subsequent mailbox work.

That live projection SHALL coexist with the persisted manifest mailbox payload rather than replacing it:

- the manifest remains the durable mailbox capability record for resume, registry publication, and gateway adapter construction,
- the tmux session env carries the effective live mailbox projection for the current tmux-contained session,
- inherited provider process env MAY remain as a launch-time snapshot but SHALL NOT be the only authoritative live mailbox source after late mailbox mutation.

When runtime-owned mailbox mutation changes the effective mailbox binding for a tmux-backed managed session, the runtime SHALL update or unset the targeted mailbox env vars in that tmux session without requiring provider relaunch solely for mailbox binding refresh.

When the selected transport requires session-local materialization before direct mailbox work is actionable, the runtime SHALL complete that materialization before publishing the refreshed live mailbox projection.

#### Scenario: Late filesystem mailbox registration refreshes live mailbox projection without relaunch
- **WHEN** the runtime late-registers a filesystem mailbox binding for a tmux-backed managed session
- **THEN** it persists the mailbox binding into the session manifest
- **AND THEN** it publishes the current common and filesystem-specific `AGENTSYS_MAILBOX_*` values plus the refreshed `AGENTSYS_MAILBOX_BINDINGS_VERSION` into the owning tmux session environment
- **AND THEN** subsequent mailbox-related work for that managed session can resolve the refreshed mailbox binding without requiring provider relaunch solely for mailbox env refresh

#### Scenario: Late mailbox unregistration clears the live tmux mailbox projection
- **WHEN** the runtime late-unregisters mailbox support from a tmux-backed managed session
- **THEN** it removes the durable mailbox binding from the session manifest
- **AND THEN** it unsets the targeted mailbox binding env vars from the owning tmux session environment
- **AND THEN** subsequent mailbox-related work for that session no longer treats it as mailbox-enabled

#### Scenario: Stalwart live mailbox projection waits for session-local credential materialization
- **WHEN** the runtime refreshes or late-registers a `stalwart` mailbox binding for a tmux-backed managed session
- **THEN** it preserves the secret-free durable transport metadata in the manifest
- **AND THEN** it materializes or validates the session-local credential file needed for direct mailbox work before publishing the live `AGENTSYS_MAILBOX_EMAIL_*` projection into tmux session environment
- **AND THEN** the live mailbox binding is not treated as actionable until that session-local credential material is available
