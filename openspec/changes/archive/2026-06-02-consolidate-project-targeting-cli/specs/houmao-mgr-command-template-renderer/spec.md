## ADDED Requirements

### Requirement: Command templates use consolidated project targeting
The maintained command-template registry SHALL render ordinary project commands through `houmao-mgr project` command paths.

Project-scoped templates SHALL support an optional project-directory field that renders as the group-level `--project-dir <dir>` option before the nested project subcommand.

The maintained public template ids SHALL NOT include top-level target-variant credentials or top-level brain-build templates.

#### Scenario: Project credential template renders project directory selector
- **WHEN** an agent renders a project Codex credential list template with project directory `/repo`
- **THEN** the rendered argv starts with `houmao-mgr project --project-dir /repo credentials codex list`
- **AND THEN** the rendered argv does not start with `houmao-mgr credentials --project`

#### Scenario: Public templates omit top-level brain build
- **WHEN** an agent lists maintained public command templates
- **THEN** the list does not include a top-level `brains.build` template id
- **AND THEN** direct build plumbing is represented only by an internal native-agent template id when retained

### Requirement: Command templates expose internal native-agent credential and brain build paths
The maintained command-template registry SHALL expose internal templates for retained direct native-agent credential CRUD and direct brain build plumbing.

Internal native-agent templates SHALL render `--native-agent-root <dir>` instead of `--agent-def-dir <dir>`.

#### Scenario: Native credential template renders native-agent root
- **WHEN** an agent renders an internal Codex native credential get template with native-agent root `/tmp/native` and credential `work`
- **THEN** the rendered argv represents `houmao-mgr internals native-agent credentials codex get --native-agent-root /tmp/native --name work`
- **AND THEN** the rendered argv does not include `--agent-def-dir`

#### Scenario: Native brain build template renders internal path
- **WHEN** an agent renders an internal native brain build template with native-agent root `/tmp/native` and preset `reviewer`
- **THEN** the rendered argv represents `houmao-mgr internals native-agent brain build --native-agent-root /tmp/native --preset reviewer`
- **AND THEN** the rendered argv does not use top-level `houmao-mgr brains build`
