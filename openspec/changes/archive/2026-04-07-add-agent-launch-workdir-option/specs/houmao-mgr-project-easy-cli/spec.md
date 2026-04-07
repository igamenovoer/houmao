## MODIFIED Requirements

### Requirement: `project easy instance launch` derives provider from one specialist and launches one runtime instance
`houmao-mgr project easy instance launch --specialist <specialist> --name <instance>` SHALL launch one managed agent by resolving the stored specialist definition from the active project-local catalog and delegating to the existing native managed-agent launch flow.

The command MAY accept `--workdir <path>` as an explicit runtime working directory for the launched agent session.

When `--workdir` is omitted, the launched runtime workdir SHALL default to the invocation cwd.

When no active project overlay exists for the caller and no stronger overlay selection override is supplied, the command SHALL ensure `<cwd>/.houmao` exists before launch preparation begins.

When no stronger explicit or env-var override is supplied, easy instance launch SHALL use overlay-local defaults for:

- runtime root: `<active-overlay>/runtime`
- jobs root: `<active-overlay>/jobs`
- mailbox root: `<active-overlay>/mailbox` for project-aware mailbox defaults

The selected project overlay and stored specialist source SHALL remain authoritative for easy launch source resolution even when `--workdir` points somewhere else.

The launch provider SHALL still be derived from the specialist's selected tool, and the command SHALL still honor stored specialist launch posture and mailbox validation rules.

The command SHALL NOT expose or require a separate launch-time workspace-trust bypass flag on this surface.

The delegated native launch SHALL proceed without a Houmao-managed workspace trust confirmation prompt.

When the stored specialist launch posture is `unattended`, any maintained no-prompt or full-autonomy provider startup posture SHALL remain owned by the resolved prompt mode and downstream launch policy.

When the stored specialist launch posture is `as_is`, easy instance launch SHALL NOT inject a separate yolo-style startup override and SHALL leave provider startup behavior untouched beyond the existing delegated launch contract.

#### Scenario: Easy instance launch uses overlay-local runtime and jobs defaults
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **AND WHEN** no stronger runtime-root or jobs-root override is supplied
- **THEN** the resulting brain build and runtime session use `/repo/.houmao/runtime`
- **AND THEN** the session-local job dir is derived under `/repo/.houmao/jobs/<session-id>/`

#### Scenario: Easy instance launch keeps the selected project overlay when `--workdir` points outside the project
- **WHEN** an active project overlay resolves as `/repo-a/.houmao`
- **AND WHEN** specialist `researcher` is stored in that project-local catalog
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --workdir /repo-b`
- **THEN** the launch resolves the specialist, runtime root, jobs root, and mailbox root from `/repo-a/.houmao`
- **AND THEN** it records `/repo-b` as the launched runtime workdir
- **AND THEN** it does not retarget specialist or overlay resolution to `/repo-b`

#### Scenario: Easy instance launch bootstraps the missing overlay before launch
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **THEN** the command ensures `<cwd>/.houmao` exists before resolving the specialist-backed launch
- **AND THEN** the launch uses that resulting overlay as the default local root family

#### Scenario: Easy instance launch does not bootstrap the runtime workdir as a project overlay
- **WHEN** no active project overlay exists for the invocation cwd
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --workdir /repo-b`
- **THEN** the command bootstraps the selected invocation overlay candidate before launch preparation begins
- **AND THEN** it does not bootstrap `/repo-b/.houmao` only because `/repo-b` was selected as the runtime workdir

#### Scenario: Stored as-is posture launches without a separate yolo-style override
- **WHEN** specialist `researcher` stores `launch.prompt_mode: as_is`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **THEN** the command delegates to native launch without a Houmao-managed workspace trust confirmation prompt
- **AND THEN** it does not inject a separate yolo-style startup override on top of the stored `as_is` posture
