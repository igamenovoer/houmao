## ADDED Requirements

### Requirement: Easy-specialist conceptual guide exists

The getting-started section SHALL include a page at `docs/getting-started/easy-specialists.md` documenting the easy-specialist and easy-instance model. The page SHALL explain:

- What an easy-specialist is: a lightweight, project-local agent definition that bundles a role, tool, setup, auth, optional skills, and launch arguments into a single named configuration.
- When to use easy-specialist vs full role/preset definitions: easy-specialist is the recommended path for operators who want a quick, opinionated agent setup; full role/preset definitions are for operators who need fine-grained control over the build phase.
- The specialist-to-instance lifecycle: `specialist create` defines the template, `instance launch` creates a running managed agent from it, `instance stop` shuts it down.
- Relationship to managed agents: an easy-instance IS a managed agent — it appears in `agents list`, can be targeted by `agents prompt`, `agents gateway`, `agents mail`, etc.
- CLI commands: `project easy specialist create|list|get|remove` and `project easy instance launch|list|get|stop`.

The page SHALL be derived from `project/easy.py` and `srv_ctrl/commands/project.py` easy-specialist command implementations.

#### Scenario: Reader understands easy-specialist vs full presets

- **WHEN** a reader opens the easy-specialist guide
- **THEN** they find a clear comparison explaining that easy-specialist is a convenience layer over the full preset system
- **AND THEN** they understand that easy-specialist bundles role + tool + setup + auth into one named definition rather than requiring separate preset YAML files

#### Scenario: Reader can create and launch an easy-specialist

- **WHEN** a reader follows the easy-specialist guide
- **THEN** they find step-by-step commands: `project easy specialist create --name <name> --role <role> --tool <tool> --setup <setup> --auth <auth>`, then `project easy instance launch --specialist <name>`
- **AND THEN** they understand that the launched instance is a managed agent controllable via standard `agents` commands

#### Scenario: Reader understands instance lifecycle

- **WHEN** a reader wants to manage easy-specialist instances
- **THEN** the page documents `instance list` for discovery, `instance get` for detailed state, and `instance stop` for shutdown
- **AND THEN** the page explains that instances are tracked in the shared registry like any other managed agent
