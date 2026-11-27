# Spec Delta

## MODIFIED Requirements

### Requirement: Project-backed Kimi unattended launch delegates to maintained automatic posture
When a selected Kimi specialist or Kimi-backed project profile resolves `launch.prompt_mode: unattended`, `houmao-mgr project agents launch` SHALL delegate to the managed native launch path in a way that lets the selected downstream Kimi adapter establish native `auto` and reject a conflicting effective permission value.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

For Kimi specialists and profiles, unattended prompt mode SHALL NOT imply headless launch. Kimi project launch SHALL apply unattended policy to the selected run mode. With no selected mode, the maintained TUI remains the project default.

When a selected Kimi specialist or Kimi-backed project profile resolves `launch.prompt_mode: as_is`, project launch SHALL preserve as-is behavior and SHALL NOT inject a separate provider auto, yolo, or unattended override.

#### Scenario: Kimi project specialist launches TUI unattended automatically
- **WHEN** a project specialist `writer` exists with tool `kimi` and stored `launch.prompt_mode: unattended`
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist writer --name writer-1` without a mode override
- **THEN** the command delegates to native launch with Kimi local-interactive posture
- **AND THEN** the resulting launch resolves the maintained Kimi unattended local-interactive policy

#### Scenario: Kimi project profile launches TUI unattended automatically
- **WHEN** project profile `writer-profile` targets a Kimi specialist and stores prompt mode `unattended`
- **AND WHEN** an operator runs `houmao-mgr project agents launch --profile writer-profile`
- **THEN** the command delegates to native launch with the stored unattended prompt mode
- **AND THEN** the resulting Kimi TUI launch is expected to run without tool approval or user-question prompts

#### Scenario: Kimi as-is project launch remains manual
- **WHEN** a project specialist `writer` exists with tool `kimi` and stored `launch.prompt_mode: as_is`
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist writer --name writer-1`
- **THEN** the command delegates to native launch with as-is prompt mode
- **AND THEN** it does not request Kimi auto permission mode through launch policy or runtime startup refresh

#### Scenario: Kimi project launch reports a conflicting effective permission setting

- **WHEN** an unattended Kimi specialist or project profile resolves an effective `manual` or `yolo` permission setting
- **THEN** project launch reports the conflict through the shared permission validation before provider start or replacement
- **AND THEN** an omitted or matching setting continues to use the requested qualified run mode

### Requirement: `project agents launch` derives provider from one specialist and launches one runtime instance
`houmao-mgr project agents launch --specialist <specialist> --name <instance>` SHALL launch one managed agent by resolving the stored specialist definition from the active project-local catalog and delegating to the existing native managed-agent launch flow.

The command MAY accept `--workdir <path>` as an explicit runtime working directory for the launched agent session.

When `--workdir` is omitted, the launched runtime workdir SHALL default to the invocation cwd.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

When no active project overlay exists for the caller and no stronger overlay selection override is supplied, the command SHALL ensure `<cwd>/.houmao` exists before launch preparation begins.

When no stronger explicit or env-var override is supplied, easy instance launch SHALL use overlay-local defaults for:

- runtime root: `<active-overlay>/runtime`
- jobs root: `<active-overlay>/jobs`
- mailbox root: `<active-overlay>/mailbox` for project-aware mailbox defaults

The launch provider SHALL still be derived from the specialist's selected tool, and the command SHALL still honor stored specialist launch posture and mailbox validation rules.

The selected project overlay and stored specialist source SHALL remain authoritative for easy launch source resolution even when `--workdir` points somewhere else.

The command SHALL NOT expose or require a separate launch-time workspace-trust bypass flag on this surface.

The delegated native launch SHALL proceed without a Houmao-managed workspace trust confirmation prompt.

Easy instance launch SHALL delegate the resolved prompt mode and authored tool settings to the native launch flow. `unattended` SHALL require the qualified maximum native permission posture and reject conflicting effective permission settings. `as_is` SHALL honor supported authored permissions and use the native baseline for omissions. Supported settings unrelated to permission posture SHALL follow existing precedence in both modes.

#### Scenario: Easy instance launch uses overlay-local runtime and jobs defaults
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist researcher --name repo-research-1`
- **AND WHEN** no stronger runtime-root or jobs-root override is supplied
- **THEN** the resulting brain build and runtime session use `/repo/.houmao/runtime`
- **AND THEN** the session-local job dir is derived under `/repo/.houmao/jobs/<session-id>/`

#### Scenario: Easy instance launch keeps the selected project overlay when `--workdir` points outside the project
- **WHEN** an active project overlay resolves as `/repo-a/.houmao`
- **AND WHEN** specialist `researcher` is stored in that project-local catalog
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist researcher --name repo-research-1 --workdir /repo-b`
- **THEN** the launch resolves the specialist, runtime root, jobs root, and mailbox root from `/repo-a/.houmao`
- **AND THEN** it records `/repo-b` as the launched runtime workdir
- **AND THEN** it does not retarget specialist or overlay resolution to `/repo-b`

#### Scenario: Easy instance launch bootstraps the missing overlay before launch
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist researcher --name repo-research-1`
- **THEN** the command ensures `<cwd>/.houmao` exists before resolving the specialist-backed launch
- **AND THEN** the launch uses that resulting overlay as the default local root family

#### Scenario: Easy instance launch does not bootstrap the runtime workdir as a project overlay
- **WHEN** no active project overlay exists for the invocation cwd
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist researcher --name repo-research-1 --workdir /repo-b`
- **THEN** the command bootstraps the selected invocation overlay candidate before launch preparation begins
- **AND THEN** it does not bootstrap `/repo-b/.houmao` only because `/repo-b` was selected as the runtime workdir

#### Scenario: Stored as-is posture launches without a separate yolo-style override
- **WHEN** specialist `researcher` stores `launch.prompt_mode: as_is`
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist researcher --name repo-research-1`
- **THEN** the command delegates to native launch without a Houmao-managed workspace trust confirmation prompt
- **AND THEN** it does not inject a separate yolo-style startup override on top of the stored `as_is` posture

#### Scenario: An unattended specialist includes an authored sandbox override
- **WHEN** an unattended specialist supplies a native sandbox value that conflicts with the selected provider's unattended posture
- **THEN** the delegated launch reports the sandbox conflict and directs the operator to `as_is` for supported custom permissions
- **AND THEN** the command starts no provider and leaves an existing instance intact

#### Scenario: An as-is specialist retains a supported custom sandbox

- **WHEN** an `as_is` specialist supplies a supported nondefault native sandbox value in its tool parameters
- **THEN** the delegated launch applies that sandbox value
- **AND THEN** omitted permission fields use the provider's native baseline
