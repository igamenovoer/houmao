## ADDED Requirements

### Requirement: CLI reference documents the dedicated credential-management families
The CLI reference SHALL document the dedicated credential-management families for `houmao-mgr`.

At minimum, that coverage SHALL include:

- the top-level `credentials` command family,
- the project-scoped `project credentials` wrapper,
- the supported tool lanes `claude`, `codex`, and `gemini`,
- the supported verbs `list`, `get`, `add`, `set`, `rename`, and `remove`,
- the target-selection model for project-backed versus `--agent-def-dir` usage,
- the removal of credential CRUD from `project agents tools <tool>`.

The `houmao-mgr` reference SHALL position `credentials` as the first-class credential-management surface and SHALL position `project credentials` as the explicit project-scoped wrapper.

#### Scenario: Reader can find the dedicated top-level credential family
- **WHEN** a reader looks up `houmao-mgr`
- **THEN** the CLI reference documents `credentials` as a supported top-level command family
- **AND THEN** the page explains when to use `credentials ...` versus `project credentials ...`

#### Scenario: Reader sees that credential CRUD moved out of project agents tools
- **WHEN** a reader checks the CLI reference for project-local tool management
- **THEN** the reference explains that `project agents tools <tool>` remains for tool inspection and setup bundles
- **AND THEN** the reference directs credential CRUD to `credentials ...` or `project credentials ...`
