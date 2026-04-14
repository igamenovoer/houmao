## REMOVED Requirements

### Requirement: `houmao-mgr agents cleanup session` removes stopped session envelopes and optionally the job dir
**Reason**: Session cleanup no longer owns a manifest-persisted `job_dir`; scratch is a per-agent workspace lane with explicit lane cleanup.
**Migration**: None. Backward compatibility and migration are explicitly out of scope for this change.

## ADDED Requirements

### Requirement: `houmao-mgr agents cleanup session` removes stopped session envelopes without job-dir cleanup
For one resolved local managed session, `houmao-mgr agents cleanup session` SHALL classify the runtime-owned session root as removable only when the resolved session no longer appears live on the local host.

The command SHALL NOT accept `--include-job-dir`.

The command SHALL NOT remove workspace scratch or persist lanes as an incidental effect of session-envelope cleanup.

When the session root is resolved but the manifest is missing or malformed, the command SHALL still classify the session root itself for removal when no available local evidence shows that session as still live.

The command SHALL block removal when the resolved session still appears live rather than deleting the active session envelope.

#### Scenario: Stopped session cleanup removes the session root only
- **WHEN** an operator runs `houmao-mgr agents cleanup session --manifest-path /abs/path/runtime/sessions/local_interactive/session-1/manifest.json`
- **AND WHEN** the resolved session no longer appears live on the local host
- **THEN** the cleanup result removes the session root
- **AND THEN** it does not remove the managed agent workspace scratch lane

#### Scenario: Include-job-dir flag is not supported
- **WHEN** an operator runs `houmao-mgr agents cleanup session --include-job-dir`
- **THEN** the command fails as an unsupported option
- **AND THEN** the command does not delete workspace files

### Requirement: Workspace scratch cleanup is an explicit lane-scoped cleanup action
Houmao SHALL provide a supported cleanup action that clears the addressed managed agent's scratch lane without removing the runtime session envelope or persist lane.

The cleanup action SHALL support dry-run planning with per-artifact actions.

The cleanup action SHALL require explicit managed-agent targeting and SHALL block by default when the addressed scratch lane cannot be resolved safely.

#### Scenario: Scratch cleanup clears only the scratch lane
- **WHEN** an operator runs a supported scratch cleanup command for managed agent `researcher`
- **AND WHEN** the command resolves scratch lane `/repo/.houmao/memory/agents/researcher-id/scratch`
- **THEN** the cleanup result removes contents under that scratch lane
- **AND THEN** it preserves `/repo/.houmao/memory/agents/researcher-id/persist`
