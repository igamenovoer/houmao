## MODIFIED Requirements

### Requirement: `houmao-mgr project init` bootstraps one repo-local `.houmao` overlay
`houmao-mgr project init` SHALL treat the caller's current working directory as the target project root in v1.

A successful init SHALL create:

- `<project-root>/.houmao/`
- `<project-root>/.houmao/houmao-config.toml`
- `<project-root>/.houmao/.gitignore`
- `<project-root>/.houmao/agents/`

The generated `.houmao/.gitignore` SHALL ignore all content under `.houmao/` and the command SHALL NOT modify the repository root `.gitignore`.

The generated `.houmao/houmao-config.toml` SHALL be the project-local source of truth for project-aware Houmao defaults.

The generated `.houmao/agents/` tree SHALL include the canonical local source layout:

- `skills/`
- `roles/`
- `tools/`

The generated `.houmao/agents/` tree MAY additionally include `compatibility-profiles/` only when the operator explicitly enables compatibility-profile bootstrap during init.

The generated `tools/` subtree SHALL include the packaged secret-free adapter and setup content needed for current supported tools.

When the target project overlay already exists and remains compatible, `project init` SHALL validate and preserve existing local auth bundles instead of overwriting them.

#### Scenario: Operator initializes a local Houmao overlay
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **THEN** the command creates `/repo/app/.houmao/houmao-config.toml`
- **AND THEN** it creates `/repo/app/.houmao/.gitignore` without editing `/repo/app/.gitignore`
- **AND THEN** it creates `/repo/app/.houmao/agents/` with canonical local source directories and packaged tool starter content

#### Scenario: Re-running init preserves compatible local auth state
- **WHEN** an operator already has `/repo/app/.houmao/agents/tools/claude/auth/personal/`
- **AND WHEN** they run `houmao-mgr project init` again inside `/repo/app`
- **THEN** the command validates the existing project overlay
- **AND THEN** it does not delete or overwrite that existing local auth bundle only because init was re-run

#### Scenario: Operator explicitly enables compatibility-profile bootstrap
- **WHEN** an operator runs `houmao-mgr project init --with-compatibility-profiles` inside `/repo/app`
- **THEN** the command creates `/repo/app/.houmao/agents/compatibility-profiles/`
- **AND THEN** it still creates the default `skills/`, `roles/`, and `tools/` roots

### Requirement: `houmao-mgr project init` bootstraps project source roots but does not create optional project workflow state by default
`houmao-mgr project init` SHALL bootstrap the base project overlay and canonical `.houmao/agents/` tree without creating optional compatibility metadata, mailbox state, or `easy` metadata state by default.

At minimum, `project init` SHALL NOT create:

- `.houmao/agents/compatibility-profiles/`
- `.houmao/mailbox/`
- `.houmao/easy/`

only because init was run.

#### Scenario: Project init leaves optional roots opt-in
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **THEN** the command creates the base `.houmao/` overlay and `.houmao/agents/` tree
- **AND THEN** it does not create `/repo/app/.houmao/agents/compatibility-profiles/` only because init was run
- **AND THEN** it does not create `/repo/app/.houmao/mailbox/` only because init was run
- **AND THEN** it does not create `/repo/app/.houmao/easy/` only because init was run
