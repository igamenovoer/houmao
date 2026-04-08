## MODIFIED Requirements

### Requirement: `houmao-mgr agents cleanup` resolves one local managed session from explicit or current-session authority
`houmao-mgr` SHALL expose a local `agents cleanup` command family for cleanup work that targets one managed-agent session envelope.

At minimum, that family SHALL include:

- `session`
- `logs`
- `mailbox`

Each `agents cleanup` command SHALL accept one cleanup authority from:

- `--agent-id <id>`
- `--agent-name <name>`
- `--manifest-path <path>`
- `--session-root <path>`

When none of those are provided and the command is run inside the owning tmux session, the command SHALL resolve the target through current-session metadata by:

1. preferring `HOUMAO_MANIFEST_PATH`,
2. otherwise falling back to `HOUMAO_AGENT_ID` plus exactly one fresh shared-registry record,
3. validating that the resolved manifest or shared-registry record belongs to the current tmux session.

When a selected cleanup authority yields one runtime-owned session root but the associated `manifest.json` is missing or malformed, the command SHALL treat that session root as a valid partial cleanup target for cleanup work that does not require manifest metadata.

When a fresh shared-registry record has a stale `runtime.manifest_path` but still provides a valid `runtime.session_root`, the command SHALL use that runtime-owned session root instead of failing immediately.

If neither a valid manifest nor a runtime-owned session root can be recovered from the selected authority, the command SHALL fail explicitly rather than guessing arbitrary paths.

These commands SHALL remain local-only maintenance commands and SHALL NOT accept `--port`.

#### Scenario: Current-session cleanup resolves through tmux-published manifest authority
- **WHEN** an operator runs `houmao-mgr agents cleanup session` from inside a managed tmux session
- **AND WHEN** that tmux session publishes a valid `HOUMAO_MANIFEST_PATH`
- **THEN** `houmao-mgr` resolves the cleanup target from that manifest
- **AND THEN** the operator does not need to pass an explicit selector or path

#### Scenario: Current-session cleanup falls back through shared registry when manifest metadata is stale
- **WHEN** an operator runs `houmao-mgr agents cleanup logs` from inside a managed tmux session
- **AND WHEN** `HOUMAO_MANIFEST_PATH` is missing, blank, or stale in that session
- **AND WHEN** `HOUMAO_AGENT_ID` resolves exactly one fresh shared-registry record
- **THEN** `houmao-mgr` resolves the cleanup target from that record's `runtime.manifest_path` when it is still valid, or from that record's `runtime.session_root` when the manifest pointer is stale
- **AND THEN** it still validates that the shared-registry record belongs to the current tmux session before cleaning anything

#### Scenario: Explicit manifest path remains valid after the live registry is gone
- **WHEN** an operator runs `houmao-mgr agents cleanup session --manifest-path /abs/path/runtime/sessions/local_interactive/session-1/manifest.json`
- **AND WHEN** the managed session has already been stopped and no fresh registry record remains
- **THEN** `houmao-mgr` uses that manifest as the cleanup authority when it is still readable
- **AND THEN** the command does not require the session to remain live just to address its artifacts

#### Scenario: Explicit manifest path still yields a cleanup target after the manifest file is deleted
- **WHEN** an operator runs `houmao-mgr agents cleanup logs --manifest-path /abs/path/runtime/sessions/local_interactive/session-1/manifest.json`
- **AND WHEN** that path still matches the runtime-owned session layout but the manifest file has already been deleted
- **THEN** `houmao-mgr` derives the cleanup target's session root from that path
- **AND THEN** manifest-independent cleanup may still continue from that session root

### Requirement: `houmao-mgr agents cleanup session` removes stopped session envelopes and optionally the job dir
For one resolved local managed session, `houmao-mgr agents cleanup session` SHALL classify the runtime-owned session root as removable only when the resolved session no longer appears live on the local host.

When the operator requests `--include-job-dir`, the command SHALL also classify the manifest-persisted `job_dir` for removal as part of the same cleanup result.

When the session root is resolved but the manifest is missing or malformed, the command SHALL still classify the session root itself for removal when no available local evidence shows that session as still live.

When manifest metadata required for `job_dir` cleanup is unavailable or the referenced `job_dir` is already absent, the command SHALL skip that `job_dir` cleanup instead of failing the whole cleanup command.

The command SHALL block removal when the resolved session still appears live rather than deleting the active session envelope.

#### Scenario: Stopped session cleanup removes the session root and requested job dir
- **WHEN** an operator runs `houmao-mgr agents cleanup session --manifest-path /abs/path/runtime/sessions/local_interactive/session-1/manifest.json --include-job-dir`
- **AND WHEN** the resolved session no longer appears live on the local host
- **THEN** the cleanup result removes the session root
- **AND THEN** it also removes the manifest-persisted `job_dir`

#### Scenario: Live session cleanup is blocked
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-id abc123`
- **AND WHEN** the resolved managed session still appears live on the local host
- **THEN** the cleanup result reports that session-root removal is blocked
- **AND THEN** the command does not delete the live session envelope

#### Scenario: Missing manifest still allows stopped session-root cleanup
- **WHEN** an operator runs `houmao-mgr agents cleanup session --session-root /abs/path/runtime/sessions/local_interactive/session-1 --include-job-dir`
- **AND WHEN** `manifest.json` under that session root is missing or malformed
- **AND WHEN** no available local evidence still shows that session root as live
- **THEN** the cleanup result removes the session root
- **AND THEN** it skips `job_dir` cleanup instead of failing because the manifest metadata is unavailable

## ADDED Requirements

### Requirement: Explicit managed-session cleanup treats missing session-local artifacts as non-fatal
For `houmao-mgr agents cleanup session|logs|mailbox`, when the selected authority resolves one runtime-owned session root explicitly or through fresh shared-registry fallback, already-absent candidate artifacts SHALL be treated as no-op cleanup work rather than as command-failing errors.

If `manifest.json` is missing or malformed for that resolved session root, the command SHALL continue evaluating cleanup actions that depend only on the session root and current local live-session evidence.

Cleanup actions whose required metadata cannot be recovered without a valid manifest SHALL be skipped rather than converting the whole cleanup result into a failure.

#### Scenario: Explicit log cleanup proceeds when the session manifest is missing
- **WHEN** an operator runs `houmao-mgr agents cleanup logs --session-root /abs/path/runtime/sessions/local_interactive/session-1`
- **AND WHEN** `manifest.json` is missing from that session root
- **AND WHEN** one or more disposable log or run-marker artifacts still exist under the resolved session root
- **THEN** the cleanup result evaluates and removes only the remaining disposable artifacts
- **AND THEN** the command does not fail solely because `manifest.json` is absent

#### Scenario: Explicit mailbox cleanup removes session-local secrets without a valid manifest
- **WHEN** an operator runs `houmao-mgr agents cleanup mailbox --manifest-path /abs/path/runtime/sessions/local_interactive/session-1/manifest.json`
- **AND WHEN** that manifest file is missing but `mailbox-secrets/` still exists under the derived session root
- **THEN** the cleanup result targets only that session-local `mailbox-secrets/` directory
- **AND THEN** the command does not require a valid manifest just to remove that session-local secret material

#### Scenario: Already-absent artifacts do not negate remaining cleanup work
- **WHEN** an operator runs one explicit `houmao-mgr agents cleanup logs` or `houmao-mgr agents cleanup mailbox` command against a resolved stopped session root
- **AND WHEN** some candidate artifacts are already absent before the command reaches them
- **THEN** those already-absent artifacts are treated as no-op cleanup work
- **AND THEN** the command continues evaluating and cleaning the remaining candidate artifacts without raising an error
