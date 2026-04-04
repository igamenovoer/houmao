## ADDED Requirements

### Requirement: Project-aware operations reference page exists

The agents reference SHALL include a page at `docs/reference/agents/operations/project-aware-operations.md` documenting how managed-agent commands resolve against the active project overlay. The page SHALL explain:

- What "project-aware" means: commands like `agents launch`, `agents list`, `agents state`, and others automatically discover and use the active `.houmao/` project overlay for agent definition resolution, mailbox root binding, and registry scoping.
- Resolution order: explicit `--agent-def-dir` → `HOUMAO_AGENT_DEF_DIR` → `HOUMAO_PROJECT_OVERLAY_DIR` → nearest ancestor `.houmao/houmao-config.toml` → default `<cwd>/.houmao/agents`.
- The `HOUMAO_PROJECT_DIR` environment variable as an override for selecting the project root in CI and automation contexts.
- The catalog-backed overlay storage model: how `project/catalog.py` and `project/overlay.py` resolve the overlay directory and provide `ProjectAwareLocalRoots`.
- Which commands are project-aware and what project context they consume (agent definitions, mailbox root, registry scoping).

The page SHALL be derived from `project/overlay.py`, `project/catalog.py`, and the project-aware initialization in `srv_ctrl/commands/`.

#### Scenario: Reader understands project-aware resolution

- **WHEN** a reader opens the project-aware operations page
- **THEN** they find the full resolution precedence chain for agent definition directory discovery
- **AND THEN** they understand that commands automatically discover the nearest `.houmao/` overlay without explicit flags

#### Scenario: Reader can override project resolution for CI

- **WHEN** a reader needs to run commands in a CI environment without `.houmao/` on disk
- **THEN** the page documents `HOUMAO_PROJECT_OVERLAY_DIR` and `HOUMAO_AGENT_DEF_DIR` as environment overrides
- **AND THEN** the page explains when each override is appropriate

#### Scenario: Reader understands which commands are project-aware

- **WHEN** a reader wants to know which commands use project context
- **THEN** the page lists the major project-aware command families: `agents launch`, `agents join`, `brains build`, `agents list`, `agents state`, and project-scoped mailbox operations
