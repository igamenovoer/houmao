# houmao-mgr-error-diagnostics Specification

## Purpose
Define actionable operator-facing diagnostics for maintained `houmao-mgr` command failures.

## Requirements
### Requirement: Maintained CLI failures are user-actionable
Maintained `houmao-mgr` commands SHALL render expected user, environment, project, registry, and runtime-state failures as user-actionable diagnostics.

The primary error message SHALL identify the failed operation and the root cause in operator-facing terms.

When available, the diagnostic SHALL include the affected target and concise evidence such as agent name, agent id, lifecycle state, tmux session, manifest path, session root, selected project root, mailbox root, or pair authority URL.

When a clear recovery exists, the diagnostic SHALL include a next action using maintained `houmao-mgr` command surfaces.

The primary error message MUST NOT be only a Python implementation exception class name such as `AssertionError`, `KeyError`, `RuntimeError`, or `ValueError`.

#### Scenario: Stale gateway status explains the stale authority
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice gateway status`
- **AND WHEN** the local registry record for `alice` is active but its local tmux authority is stale or missing
- **THEN** the command fails with a diagnostic that names gateway status as the failed operation
- **AND THEN** the diagnostic identifies `alice` and the managed-agent id when available
- **AND THEN** the diagnostic explains that the registry record points at stale or missing local runtime authority
- **AND THEN** the diagnostic includes a maintained recovery command such as managed-agent stop, relaunch, list, or registry cleanup
- **AND THEN** the diagnostic does not render `Error: AssertionError` as the primary error

#### Scenario: Missing local selector keeps existing actionable guidance
- **WHEN** an operator runs a maintained scoped managed-agent command with a friendly name that has no local registry match
- **AND WHEN** fallback lookup through the default pair authority also fails
- **THEN** the command fails with a diagnostic that explains no local managed agent matched the friendly name
- **AND THEN** the diagnostic includes the pair authority failure detail
- **AND THEN** the diagnostic tells the operator to retry with `houmao-mgr agents global list`, the correct friendly name, or `--agent-id`

### Requirement: Live-controller operations reject stale and degraded local targets explicitly
Managed-agent operations that require a live local runtime controller SHALL reject `local_stale` and `local_degraded` targets with an explicit `click.ClickException` before dereferencing `target.controller`.

The diagnostic SHALL distinguish operations that can mutate lifecycle recovery, such as `stop` and `relaunch`, from read/control operations that require an already-live authority, such as gateway status, gateway TUI state, gateway reminders, gateway mail-notifier status, managed-agent state, prompt, interrupt, mail status, and workspace operations.

#### Scenario: Gateway TUI command rejects stale target before controller access
- **WHEN** a gateway TUI command resolves a managed-agent target as `local_stale`
- **THEN** the command fails with a stale-authority diagnostic before reading `target.controller`
- **AND THEN** the diagnostic names the gateway TUI operation
- **AND THEN** the diagnostic includes the stale target's managed-agent evidence and a recovery command
- **AND THEN** the command does not expose a bare assertion failure

#### Scenario: Managed-agent state command rejects degraded target before controller access
- **WHEN** a managed-agent state or detail command resolves a target as `local_degraded`
- **THEN** the command fails with a degraded-authority diagnostic before reading `target.controller`
- **AND THEN** the diagnostic tells the operator that lifecycle recovery is required before state inspection can use the local authority
- **AND THEN** the command does not expose a bare assertion failure

#### Scenario: Stop keeps lifecycle recovery behavior
- **WHEN** a stop command resolves a target as `local_stale` or `local_degraded`
- **THEN** the command uses the existing lifecycle recovery behavior for broken active local records
- **AND THEN** the command does not replace that recovery path with a read-only stale-authority rejection

### Requirement: Unexpected internal failures use an explicit fallback message
The top-level `houmao-mgr` entrypoint SHALL render uncaught unexpected exceptions as internal failures rather than as normal domain errors.

For an uncaught exception with an empty message, the fallback diagnostic SHALL include a stable phrase identifying an unexpected internal error and SHALL include the exception class as diagnostic evidence.

For an uncaught exception with a non-empty message, the fallback diagnostic SHALL include the stable internal-error phrase and the exception detail.

The fallback SHALL continue to suppress Python tracebacks in normal operator output.

#### Scenario: Empty AssertionError is not the whole message
- **WHEN** a maintained command unexpectedly raises an empty `AssertionError`
- **THEN** the top-level CLI fails with an unexpected-internal-error diagnostic
- **AND THEN** the diagnostic includes `AssertionError` as evidence
- **AND THEN** the diagnostic does not render `Error: AssertionError` as the complete message
- **AND THEN** the diagnostic does not include a Python traceback

#### Scenario: Non-empty unexpected exception remains reportable
- **WHEN** a maintained command unexpectedly raises a non-domain exception with a non-empty message
- **THEN** the top-level CLI fails with an unexpected-internal-error diagnostic
- **AND THEN** the diagnostic includes the exception detail
- **AND THEN** the diagnostic does not include a Python traceback

### Requirement: Similar implementation-level CLI messages are scanned and covered
The change SHALL include a focused scan of maintained `houmao-mgr` public command paths for implementation-level error rendering patterns.

The scan SHALL cover generic `except Exception` handlers, `str(exc) or exc.__class__.__name__` renderers, `raise click.ClickException(str(exc))` conversions on public command boundaries, and assertion-backed access to `ManagedAgentTarget.client`, `ManagedAgentTarget.controller`, or `ManagedAgentTarget.record`.

Issues found by the scan SHALL be fixed in this change when they affect maintained public command output and have enough local context to produce an actionable diagnostic.

Issues that are test-only, demo-only, non-public, or require a larger design change MAY be documented as out of scope rather than fixed in this change.

#### Scenario: Public command scan drives fixes
- **WHEN** the implementation work starts
- **THEN** the maintainer scans maintained public `houmao-mgr` command paths for implementation-level error rendering patterns
- **AND THEN** each fixed issue receives focused regression coverage or is documented as out of scope in the task evidence

#### Scenario: Regression tests reject bare implementation errors
- **WHEN** focused unit tests exercise known stale/degraded target paths and root fallback paths
- **THEN** the tests assert that the output contains actionable cause or internal-error wording
- **AND THEN** the tests assert that bare implementation exception class names are not the complete primary error message

