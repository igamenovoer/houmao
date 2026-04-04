## MODIFIED Requirements

### Requirement: Runtime defaults new build and session state to the Houmao runtime root
The runtime SHALL default new build and session state to the effective project-aware runtime root when local command flows operate in project context.

When a maintained local build or launch flow has an active project overlay and no stronger runtime-root override exists, the effective runtime root SHALL be `<active-overlay>/runtime`.

When an explicit runtime-root override exists, that explicit override SHALL win.
When no active project overlay exists for the flow and the command requires local Houmao-owned state, the command SHALL ensure `<cwd>/.houmao` exists and use `<cwd>/.houmao/runtime` as the resulting default runtime root unless a stronger override applies.

Registry publication remains separate and SHALL continue to use the shared registry root rather than nesting registry state under the runtime root.

#### Scenario: Project-context build uses overlay-local runtime root
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** a maintained local brain build or runtime launch runs without a stronger runtime-root override
- **THEN** the effective runtime root is `/repo/.houmao/runtime`
- **AND THEN** generated homes, manifests, and session envelopes are written under that overlay-local runtime root

#### Scenario: Explicit runtime-root override still wins over project-aware defaulting
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** a maintained local build or launch flow is given explicit runtime-root override `/tmp/custom-runtime`
- **THEN** the effective runtime root is `/tmp/custom-runtime`
- **AND THEN** the overlay-local runtime default is not used for that operation

### Requirement: Runtime creates and reuses a per-agent job dir for each started session
For maintained local launch flows operating in project context, the runtime SHALL derive the default per-agent job dir from the active project overlay as:

- `<active-overlay>/jobs/<session-id>/`

When an explicit jobs-root override exists, that explicit override SHALL win.
When `HOUMAO_LOCAL_JOBS_DIR` is set and no stronger explicit jobs-root override exists, that env-var override SHALL win.
Maintained local launch boundaries SHALL resolve the effective jobs root before session startup and pass an explicit jobs-root or already resolved job dir into that startup path rather than relying on the caller's working directory as the implicit jobs anchor.

The runtime SHALL persist the resolved job dir in the session manifest and publish it to the launched session environment as `HOUMAO_JOB_DIR`.

#### Scenario: Project-context session derives its job dir under the overlay
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** the runtime starts a session with generated session id `session-20260314-120000Z-abcd1234`
- **AND WHEN** no stronger jobs-root override exists
- **THEN** the effective job dir is `/repo/.houmao/jobs/session-20260314-120000Z-abcd1234/`
- **AND THEN** the session manifest records that resolved path as `job_dir`

#### Scenario: Jobs env override still relocates the per-session job dir
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** `HOUMAO_LOCAL_JOBS_DIR=/tmp/houmao-jobs`
- **AND WHEN** the runtime starts a session with generated session id `session-20260314-120000Z-abcd1234`
- **THEN** the effective job dir is `/tmp/houmao-jobs/session-20260314-120000Z-abcd1234/`
- **AND THEN** the overlay-local jobs default is not used for that session

#### Scenario: Project-aware launch resolves jobs placement before session startup
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator starts a maintained local launch flow from working directory `/repo/subdir`
- **AND WHEN** no stronger jobs-root override exists
- **THEN** the launch boundary passes `/repo/.houmao/jobs` or the fully resolved `/repo/.houmao/jobs/<session-id>/` into session startup
- **AND THEN** the session does not derive its default job dir from `/repo/subdir/.houmao/jobs`
