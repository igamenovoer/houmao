# houmao-mgr-cleanup-cli Specification

## Purpose
TBD - created by archiving change add-houmao-mgr-cleanup-commands. Update Purpose after archive.
## Requirements
### Requirement: Cleanup commands support structured dry-run planning
Every `houmao-mgr` cleanup command introduced by this capability SHALL accept `--dry-run`.

When `--dry-run` is present, the command SHALL classify candidate artifacts, preserved artifacts, and blocked deletions using the same resolution and safety rules as ordinary execution, but it SHALL NOT delete or mutate any filesystem state.

Cleanup results for both dry-run and execute modes SHALL be structured and SHALL identify the resolved cleanup scope plus the reason for each planned, applied, blocked, or preserved action.

#### Scenario: Operator previews a cleanup plan without deleting anything
- **WHEN** an operator runs a supported cleanup command with `--dry-run`
- **THEN** the command returns a structured result that includes planned actions, blocked actions, and preserved artifacts
- **AND THEN** the command does not delete, rename, or mutate any candidate artifact during that run

### Requirement: `houmao-mgr admin cleanup runtime` exposes host-scoped runtime janitors
`houmao-mgr` SHALL expose a local `admin cleanup runtime` command family for cleanup work rooted under the effective runtime root.

At minimum, that family SHALL include:

- `sessions`
- `builds`
- `logs`
- `mailbox-credentials`

These commands SHALL operate on local Houmao-owned runtime state and SHALL NOT require a running pair authority.

When no stronger explicit runtime-root override exists and the command runs in project context, the effective runtime root SHALL default to `<active-overlay>/runtime`.
Each cleanup invocation SHALL target exactly one effective runtime root.
Operators who need to clean legacy shared-root artifacts under `~/.houmao/runtime` SHALL do so by supplying an explicit runtime-root override such as `--runtime-root ~/.houmao/runtime`.

#### Scenario: Project-context runtime cleanup targets the overlay-local runtime root by default
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr admin cleanup runtime builds` without `--runtime-root`
- **THEN** the command evaluates build artifacts under `/repo/.houmao/runtime`
- **AND THEN** it does not instead default to a shared runtime root under `~/.houmao/runtime`

#### Scenario: Explicit runtime-root override can still target legacy shared-root cleanup
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr admin cleanup runtime sessions --runtime-root ~/.houmao/runtime`
- **THEN** the command evaluates runtime-session artifacts under `~/.houmao/runtime`
- **AND THEN** it does not also sweep `/repo/.houmao/runtime` in that same invocation

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

### Requirement: `houmao-mgr admin cleanup runtime builds` removes only unreferenced build artifacts
`houmao-mgr admin cleanup runtime builds` SHALL evaluate build artifacts under the effective runtime root by pairing generated brain manifests with their referenced runtime homes.

The command SHALL classify a build-manifest/runtime-home pair as removable only when no preserved runtime session manifest still references that build manifest.

The command MAY also classify broken half-pairs as removable when the manifest or home counterpart is missing.

#### Scenario: Unreferenced build pair is removable
- **WHEN** a generated brain manifest and its runtime home exist under the effective runtime root
- **AND WHEN** no preserved runtime session manifest still references that brain manifest
- **THEN** `houmao-mgr admin cleanup runtime builds` classifies that manifest-home pair as removable
- **AND THEN** the cleanup result does not treat the pair as protected durable state

#### Scenario: Referenced build pair is preserved
- **WHEN** a generated brain manifest and runtime home still exist under the effective runtime root
- **AND WHEN** a preserved runtime session manifest still references that brain manifest
- **THEN** `houmao-mgr admin cleanup runtime builds` preserves that manifest-home pair
- **AND THEN** the cleanup result identifies the pair as referenced rather than stale

### Requirement: Runtime log cleanup excludes durable gateway and manifest state
`houmao-mgr admin cleanup runtime logs` and `houmao-mgr agents cleanup logs` SHALL remove only log-style or ephemeral runtime artifacts.

At minimum, runtime log cleanup MAY target:

- gateway running logs,
- gateway run-directory live-instance files,
- inactive server-root log files,
- inactive server-root run-instance files.

Runtime log cleanup SHALL NOT treat these artifacts as disposable log output in this change:

- `manifest.json`
- `gateway/queue.sqlite`
- `gateway/events.jsonl`
- `gateway/state.json`

#### Scenario: Log cleanup preserves durable gateway state
- **WHEN** an operator runs a supported runtime log cleanup command
- **THEN** the command may remove human-oriented log files and ephemeral live-instance files
- **AND THEN** it preserves durable gateway artifacts such as `queue.sqlite`, `events.jsonl`, `state.json`, and `manifest.json`

### Requirement: Runtime mailbox credential cleanup removes only unreferenced credential refs
`houmao-mgr admin cleanup runtime mailbox-credentials` SHALL evaluate runtime-owned Stalwart credential files by `credential_ref`.

The command SHALL classify a credential file as removable only when no preserved runtime session manifest still references that `credential_ref`.

#### Scenario: Referenced credential file is preserved
- **WHEN** a runtime-owned Stalwart credential file exists under the effective runtime root
- **AND WHEN** at least one preserved runtime session manifest still references that file's `credential_ref`
- **THEN** `houmao-mgr admin cleanup runtime mailbox-credentials` preserves that credential file
- **AND THEN** the cleanup result identifies the file as still referenced

#### Scenario: Unreferenced credential file is removable
- **WHEN** a runtime-owned Stalwart credential file exists under the effective runtime root
- **AND WHEN** no preserved runtime session manifest still references that file's `credential_ref`
- **THEN** `houmao-mgr admin cleanup runtime mailbox-credentials` classifies that credential file as removable
- **AND THEN** the cleanup result does not require manual source-code inspection to identify it as stale

### Requirement: `houmao-mgr agents cleanup mailbox` removes only session-local mailbox secret material
`houmao-mgr agents cleanup mailbox` SHALL target mailbox secret material scoped to one resolved managed-agent session.

At minimum, that command SHALL operate on the session-local mailbox secret directory under the resolved session root when mailbox secret material is present there.

The command SHALL NOT treat shared mailbox-root canonical message content or runtime-owned shared credential files as part of this session-scoped cleanup action.

#### Scenario: Session mailbox cleanup removes only session-local secret files
- **WHEN** an operator runs `houmao-mgr agents cleanup mailbox` against one resolved managed-agent session
- **AND WHEN** that session root contains session-local mailbox secret material
- **THEN** the cleanup result targets only that session-local mailbox secret material
- **AND THEN** it does not delete shared mailbox-root canonical message content or runtime-owned shared credential files as part of the same action

### Requirement: Human-oriented cleanup output lists per-artifact actions
Cleanup commands that emit the normalized cleanup payload SHALL render populated action buckets as per-artifact output in human-oriented print styles.

This requirement applies to cleanup command families that share the normalized cleanup payload shape, including:

- `houmao-mgr admin cleanup ...`
- `houmao-mgr agents cleanup ...`
- `houmao-mgr mailbox cleanup`
- `houmao-mgr project mailbox cleanup`

For `plain` and `fancy` print styles, each rendered action entry SHALL identify the artifact path and the cleanup reason, and it SHALL preserve enough context to distinguish artifact kind and any compact action details when present.

Human-oriented cleanup output SHALL NOT collapse populated action buckets into count-only placeholders when detailed action records are available.

`json` output SHALL continue to expose the structured cleanup payload with `planned_actions`, `applied_actions`, `blocked_actions`, `preserved_actions`, and `summary`.

#### Scenario: Plain dry-run output lists planned and preserved actions line by line
- **WHEN** an operator runs a supported cleanup command in `plain` mode with one or more `planned_actions` or `preserved_actions`
- **THEN** the output lists each action on its own line within the corresponding outcome bucket
- **AND THEN** the operator can see the artifact path and reason without switching to JSON

#### Scenario: Plain execute output lists applied and blocked actions line by line
- **WHEN** an operator runs a supported cleanup command in `plain` mode and the result contains one or more `applied_actions` or `blocked_actions`
- **THEN** the output lists each action on its own line within the corresponding outcome bucket
- **AND THEN** the output is not limited to summary counts alone

#### Scenario: JSON cleanup output remains structured
- **WHEN** an operator runs a supported cleanup command with `--print-json`
- **THEN** the output remains a structured JSON object containing the cleanup action arrays and summary fields
- **AND THEN** the command does not replace that machine-readable payload with renderer-specific plain-text lines

### Requirement: Runtime cleanup help and payload wording describe the resolved cleanup root consistently
Maintained `houmao-mgr admin cleanup runtime ...` help text and structured cleanup results SHALL describe the resolved runtime scope consistently with the project-aware root contract.

When no explicit runtime-root override wins and project context is active, help text SHALL describe the default cleanup scope as the active project runtime root.

When an explicit runtime-root override or global runtime-root env override wins, help text and cleanup results SHALL describe that scope as an explicit runtime-root selection rather than as an active project runtime root.

#### Scenario: Help text describes project-aware runtime cleanup defaults
- **WHEN** an operator runs `houmao-mgr admin cleanup runtime --help`
- **THEN** the help output explains that `--runtime-root` overrides the active project runtime root when project context is active
- **AND THEN** it does not imply that the maintained default is always a shared runtime root

#### Scenario: Cleanup result distinguishes explicit override from project-aware default
- **WHEN** an operator runs `houmao-mgr admin cleanup runtime sessions --runtime-root /tmp/houmao-runtime --dry-run`
- **THEN** the structured cleanup result identifies `/tmp/houmao-runtime` as the selected cleanup root for that invocation
- **AND THEN** the operator-facing wording does not describe that explicit override as the active project runtime root

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
