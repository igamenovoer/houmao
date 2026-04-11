## Purpose

Define the expected module layout and public entrypoint stability for the `houmao-mgr project` command implementation.

## Requirements

### Requirement: Project command implementation is decomposed by command family
The `houmao-mgr project` command implementation SHALL be split across focused modules instead of keeping all project command handlers and helpers in one oversized module.

At minimum, the split SHALL preserve separate ownership for:

- project root group registration and `init` / `status`
- shared project command helpers
- `project agents tools ...`
- `project agents roles ...`, `project agents presets ...`, and `project agents recipes ...`
- `project agents launch-profiles ...`
- `project easy ...`
- `project mailbox ...`

#### Scenario: Command families have focused module owners
- **WHEN** a developer inspects the project command implementation
- **THEN** the command handlers for project tools, project definitions, launch profiles, easy workflows, and project mailbox workflows are not all defined in `src/houmao/srv_ctrl/commands/project.py`
- **AND THEN** each extracted command family has a module whose name and contents match that family closely enough for a maintainer to find the relevant handlers without scanning unrelated project command families

#### Scenario: Shared helpers avoid a replacement oversized utility module
- **WHEN** shared project command helper code is extracted
- **THEN** helpers that are only used by one project command family remain in that family module
- **AND THEN** the shared helper module contains only helpers used by multiple command families or by the project root entrypoint

### Requirement: Project command public entrypoint remains stable
The module `houmao.srv_ctrl.commands.project` SHALL remain the stable public command entrypoint for the top-level CLI and SHALL continue to expose `project_group`.

The refactor SHALL preserve the user-facing `houmao-mgr project ...` command tree and structured payload behavior.

#### Scenario: Top-level CLI imports the project group from the stable module
- **WHEN** the top-level `houmao-mgr` Click tree is assembled
- **THEN** it can import `project_group` from `houmao.srv_ctrl.commands.project`
- **AND THEN** `houmao-mgr project --help` still lists `init`, `status`, `agents`, `easy`, `credentials`, and `mailbox`

#### Scenario: Extracted modules preserve existing project command behavior
- **WHEN** the existing focused project command unit tests are run after the module split
- **THEN** behavior covered by those tests remains unchanged except for intentional private helper import-path updates inside tests
- **AND THEN** project command output payloads and operator-facing errors remain behaviorally compatible

### Requirement: Project command refactor removes confirmed-dead helper code
The implementation SHALL identify project-local helper code that has been superseded by dedicated modules and remove it when repository search and focused tests confirm that it has no runtime callers.

If caller analysis is inconclusive, the helper code MAY be moved to the narrowest owning module and deleted in a later change.

#### Scenario: Superseded credential helpers are not moved blindly
- **WHEN** a project-local helper cluster duplicates behavior already owned by `houmao.srv_ctrl.commands.credentials`
- **THEN** the implementation checks for runtime callers before moving that helper cluster
- **AND THEN** confirmed-dead helpers are deleted instead of being preserved in a new module

#### Scenario: Uncertain helper ownership is handled conservatively
- **WHEN** a helper's runtime callers or ownership are unclear during the refactor
- **THEN** the helper remains available through an owning project command module until follow-up deletion can be justified
- **AND THEN** behavior-preserving tests are used before and after any deletion
