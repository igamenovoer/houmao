## Why

Houmao is still pre-1.0 and its persisted source/runtime formats are changing quickly; maintaining in-place migrations and legacy-input adoption paths makes the source harder to reason about and can mask incompatibilities as best-effort repairs.

When a persisted or source format becomes incompatible, operators should restart from scratch by recreating the affected Houmao project, mailbox root, runtime session, gateway root, generated home, or system-skill installation instead of relying on unmaintained compatibility transforms.

## What Changes

- **BREAKING**: Remove in-place project catalog schema migration paths for older catalog versions and older catalog table constraints.
- **BREAKING**: Remove automatic import of legacy tree-backed project-local specialist/easy metadata into the SQLite project catalog.
- **BREAKING**: Remove filesystem mailbox migration from legacy shared mutable mailbox state into mailbox-local SQLite state.
- **BREAKING**: Remove in-memory session manifest upgrades from older runtime manifest schemas into the current manifest shape.
- **BREAKING**: Remove legacy brain recipe parsing, hidden legacy build flags, and old tool-adapter field aliases from maintained construction paths.
- **BREAKING**: Remove system-skill install-state/path migration for old copy-only records, old family-namespaced paths, and renamed skill records.
- **BREAKING**: Remove gateway queue/notifier SQLite schema upgrade behavior for older gateway roots.
- Keep fresh project, mailbox, runtime session, gateway, generated home, and system-skill creation on the current schema/format.
- Keep explicit fail-fast behavior for incompatible persisted stores and unsupported source shapes, with errors that tell the operator what to recreate.
- Preserve recovery or repair flows that rebuild supported current-format indexes from canonical artifacts, such as mailbox message Markdown, when those flows are not old-format migrations.
- Remove tests and documentation that present old-format migration or legacy source adoption as supported behavior.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `project-config-catalog`: Project catalog compatibility behavior changes from in-place migration/import to current-format creation plus explicit incompatibility failure.
- `agent-mailbox-fs-transport`: Filesystem mailbox compatibility behavior changes by removing legacy shared-state-to-local-state migration while retaining current-format recovery from canonical mailbox artifacts.
- `brain-launch-runtime`: Runtime session manifest loading changes from in-memory v2/v3 upgrade to current-schema-only validation and explicit restart guidance.
- `component-agent-construction`: Agent construction source parsing changes by rejecting legacy recipe files, hidden legacy build aliases, and old tool-adapter field aliases.
- `houmao-system-skill-installation`: System-skill installer behavior changes from migrating old owned install state and paths to current install-state-only management plus explicit reinstall guidance.
- `agent-gateway`: Gateway durable queue/notifier state changes from in-place SQLite schema upgrade to current-schema creation plus explicit gateway-root recreation guidance.

## Impact

- Affected source: project catalog initialization/import code, filesystem mailbox local-state bootstrap, session manifest parsing, brain construction source parsing, system-skill install-state handling, and gateway durable queue schema setup.
- Affected tests: migration/import/legacy-adoption tests should be removed or replaced with current-format creation and unsupported-format failure tests.
- Affected docs: documentation should stop promising source or persisted-state migrations and should direct operators to recreate the relevant Houmao-owned state when formats are incompatible.
- No new dependencies.
