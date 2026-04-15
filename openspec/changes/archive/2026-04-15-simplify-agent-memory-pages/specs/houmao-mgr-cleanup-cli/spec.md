## MODIFIED Requirements

### Requirement: `houmao-mgr agents cleanup session` removes stopped session envelopes without job-dir cleanup
For one resolved local managed session, `houmao-mgr agents cleanup session` SHALL classify the runtime-owned session root as removable only when the resolved session no longer appears live on the local host.

The command SHALL NOT accept `--include-job-dir`.

The command SHALL NOT remove the managed-agent memory root, memo file, or pages directory as an incidental effect of session-envelope cleanup.

When the session root is resolved but the manifest is missing or malformed, the command SHALL still classify the session root itself for removal when no available local evidence shows that session as still live.

The command SHALL block removal when the resolved session still appears live rather than deleting the active session envelope.

#### Scenario: Stopped session cleanup removes the session root only
- **WHEN** an operator runs `houmao-mgr agents cleanup session --manifest-path /abs/path/runtime/sessions/local_interactive/session-1/manifest.json`
- **AND WHEN** the resolved session no longer appears live on the local host
- **THEN** the cleanup result removes the session root
- **AND THEN** it does not remove the managed agent memory root
- **AND THEN** it does not remove the managed agent pages directory

#### Scenario: Include-job-dir flag is not supported
- **WHEN** an operator runs `houmao-mgr agents cleanup session --include-job-dir`
- **THEN** the command fails as an unsupported option
- **AND THEN** the command does not delete managed memory files

## REMOVED Requirements

### Requirement: Workspace scratch cleanup is an explicit lane-scoped cleanup action
**Reason**: There is no managed scratch lane after the memo-pages simplification.

**Migration**: Remove scratch cleanup commands. Operators may edit or delete memo pages explicitly through supported memory page operations.
