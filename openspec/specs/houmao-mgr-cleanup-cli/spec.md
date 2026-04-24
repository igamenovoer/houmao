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

### Requirement: Managed-session cleanup resolves stopped lifecycle registry records
`houmao-mgr agents cleanup session|logs|mailbox` SHALL resolve stopped lifecycle-aware registry records by `--agent-id` and `--agent-name` when those records preserve runtime manifest or session-root authority.

When a stopped lifecycle registry record resolves to a valid runtime-owned session root, cleanup SHALL use that registry record as the cleanup authority rather than requiring a runtime-root scan.

When both a lifecycle registry record and a stopped runtime-root scan candidate match the same selector, the lifecycle registry record SHALL be preferred as the authoritative target.

When multiple stopped lifecycle records match a friendly name, cleanup SHALL fail explicitly and SHALL list candidate agent ids, lifecycle states, manifest paths, and session roots.

#### Scenario: Cleanup resolves stopped record by friendly name
- **WHEN** an operator runs `houmao-mgr agents cleanup logs --agent-name reviewer`
- **AND WHEN** exactly one stopped lifecycle registry record stores `agent_name = "reviewer"` and a valid session root
- **THEN** cleanup resolves that stopped registry record as the target
- **AND THEN** cleanup does not require the operator to copy `--manifest-path` or `--session-root` from the earlier stop output

#### Scenario: Cleanup prefers registry record over stopped runtime scan
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-id agent-123`
- **AND WHEN** the lifecycle registry contains a stopped record for `agent-123`
- **AND WHEN** a runtime-root scan also finds a matching stopped manifest
- **THEN** cleanup uses the registry record as the authoritative identity and locator source
- **AND THEN** the runtime-root scan does not select a different target

#### Scenario: Cleanup stopped friendly-name ambiguity fails closed
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-name reviewer`
- **AND WHEN** two stopped lifecycle registry records store `agent_name = "reviewer"`
- **THEN** cleanup fails explicitly
- **AND THEN** the error lists candidate `agent_id`, lifecycle state, manifest path, and session root values

### Requirement: Managed-session cleanup retires or purges stopped registry records
When `houmao-mgr agents cleanup session` removes or validates removal of a stopped managed-agent session root, the command SHALL update the corresponding lifecycle-aware registry record so that future relaunch does not target deleted runtime artifacts.

By default, cleanup SHOULD mark the registry record as `retired` when the registry record remains useful for audit and diagnostics. The cleanup surface SHALL provide an explicit purge mode to delete the registry record entirely when the operator wants to remove the lifecycle index entry.

Retired registry records SHALL NOT be considered relaunchable and SHALL NOT be included in active list output. Lifecycle-inclusive listing MAY show retired records only when explicitly requested.

#### Scenario: Session cleanup retires stopped record by default
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-name reviewer`
- **AND WHEN** cleanup removes the stopped session root for a lifecycle registry record
- **THEN** the registry record transitions to lifecycle state `retired`
- **AND THEN** future `houmao-mgr agents relaunch --agent-name reviewer` fails with an explicit retired-record message

#### Scenario: Session cleanup purge deletes registry record
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-name reviewer --purge-registry`
- **AND WHEN** cleanup removes the stopped session root for a lifecycle registry record
- **THEN** the registry record is deleted from the managed-agent registry
- **AND THEN** future selector lookup does not find that managed-agent record

#### Scenario: Dry-run cleanup reports registry lifecycle action
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-id agent-123 --dry-run`
- **AND WHEN** the selected stopped registry record would be retired or purged during execute mode
- **THEN** the dry-run cleanup payload includes the planned registry lifecycle action
- **AND THEN** the registry record is not mutated during dry-run

### Requirement: Cleanup preserves active lifecycle records unless explicitly forced through supported live safeguards
Cleanup commands SHALL NOT remove or retire active lifecycle registry records merely because they match an agent name or id.

When cleanup resolves an active record, it SHALL apply the existing live-session safety checks before removing runtime artifacts. If live cleanup is unsupported for the selected action, cleanup SHALL fail explicitly and direct the operator to stop the agent first.

#### Scenario: Cleanup refuses active session root without stop
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-name reviewer`
- **AND WHEN** `reviewer` resolves to an active lifecycle registry record with a live tmux session
- **THEN** cleanup refuses to remove the active session root
- **AND THEN** the error instructs the operator to stop the agent or use an explicit supported force-cleanup flow

#### Scenario: Log cleanup can preserve durable active state
- **WHEN** an operator runs `houmao-mgr agents cleanup logs --agent-id agent-123`
- **AND WHEN** `agent-123` resolves to an active lifecycle registry record
- **THEN** cleanup does not retire or purge the registry record
- **AND THEN** any supported log cleanup still preserves durable manifest, gateway queue, events, and state artifacts

### Requirement: Agent cleanup selectors recover stopped sessions from the runtime root
When `houmao-mgr agents cleanup session|logs|mailbox` is invoked with `--agent-id` or `--agent-name` and no fresh shared-registry record exists for that selector, the command SHALL attempt a cleanup-only fallback scan of the effective local runtime root for runtime-owned session envelopes.

The fallback scan SHALL match only persisted session manifests whose `agent_id` or `agent_name` equals the selected cleanup identity. The fallback SHALL NOT make stopped sessions visible to live-control commands such as prompt, interrupt, state, gateway, or mail operations.

When the fallback finds exactly one matching stopped session envelope, the cleanup command SHALL resolve that envelope as the cleanup target and SHALL continue using the existing live-session safety checks before deleting session roots or cleanup-sensitive artifacts.

When the fallback finds multiple matching stopped session envelopes, the cleanup command SHALL fail explicitly with enough candidate metadata for the operator to rerun cleanup with `--manifest-path` or `--session-root`.

When neither fresh registry resolution nor runtime-root fallback finds a target, the cleanup command SHALL fail explicitly and SHALL direct the operator to provide `--manifest-path`, `--session-root`, or the appropriate runtime-root selection when the desired stopped session lives outside the effective runtime root.

The system SHALL NOT create or depend on stopped-session tombstones, stopped-agent indexes, or additional shared-registry records for this fallback.

#### Scenario: Stopped session cleanup recovers by agent id after registry removal
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-id agent-123`
- **AND WHEN** no fresh shared-registry record exists for `agent-123`
- **AND WHEN** exactly one stopped runtime session manifest under the effective runtime root contains `agent_id = "agent-123"`
- **THEN** the command resolves that stopped session envelope as the cleanup target
- **AND THEN** cleanup does not require a live shared-registry record for that stopped session

#### Scenario: Stopped session cleanup recovers by friendly name after registry removal
- **WHEN** an operator runs `houmao-mgr agents cleanup logs --agent-name reviewer`
- **AND WHEN** no fresh shared-registry record exists for `reviewer`
- **AND WHEN** exactly one stopped runtime session manifest under the effective runtime root contains `agent_name = "reviewer"`
- **THEN** the command resolves that stopped session envelope as the cleanup target
- **AND THEN** the command reports the resolved `manifest_path` and `session_root` in its cleanup scope or action details

#### Scenario: Ambiguous stopped cleanup selector fails closed
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-name reviewer`
- **AND WHEN** no fresh shared-registry record exists for `reviewer`
- **AND WHEN** more than one stopped runtime session manifest under the effective runtime root contains `agent_name = "reviewer"`
- **THEN** the command fails with an ambiguity error
- **AND THEN** the error includes candidate cleanup locators such as `agent_id`, `agent_name`, `manifest_path`, and `session_root`

#### Scenario: Cleanup fallback does not address live control
- **WHEN** no fresh shared-registry record exists for `reviewer`
- **AND WHEN** a stopped runtime session manifest under the effective runtime root contains `agent_name = "reviewer"`
- **THEN** `houmao-mgr agents cleanup session --agent-name reviewer` may use runtime-root fallback for cleanup
- **AND THEN** `houmao-mgr agents prompt --agent-name reviewer` does not use that stopped manifest as a live-control target

#### Scenario: No stopped cleanup match remains explicit
- **WHEN** an operator runs `houmao-mgr agents cleanup mailbox --agent-id missing-agent`
- **AND WHEN** no fresh shared-registry record exists for `missing-agent`
- **AND WHEN** no stopped runtime session manifest under the effective runtime root contains `agent_id = "missing-agent"`
- **THEN** the command fails explicitly
- **AND THEN** the error tells the operator to provide a durable cleanup locator such as `--manifest-path` or `--session-root`

### Requirement: Cleanup commands keep destructive filesystem actions contained to owned artifacts
`houmao-mgr` cleanup commands SHALL delete only owned runtime, session, log, mailbox, or registry artifacts selected through a validated cleanup authority.

If cleanup resolution determines that the selected artifact path escapes the applicable owned root, the command SHALL fail clearly before mutating the filesystem.

If the selected artifact path itself is a symlink, cleanup SHALL treat that symlink as the artifact and SHALL NOT recursively delete its target.

#### Scenario: Cleanup rejects an escaped owned-root mutation target
- **WHEN** cleanup resolution produces one candidate artifact path that is not contained within the applicable owned runtime or registry root
- **THEN** the cleanup command fails clearly before mutating the filesystem

#### Scenario: Cleanup removes a symlink artifact without deleting its target
- **WHEN** one cleanup command is authorized to remove one owned artifact path
- **AND WHEN** that artifact path currently exists as a symlink to a directory outside the owned root
- **THEN** cleanup removes only the symlink artifact path
- **AND THEN** it does not recursively delete the symlink target
