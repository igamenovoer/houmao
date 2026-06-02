## ADDED Requirements

### Requirement: Command templates use explicit agent scope paths
The maintained command-template registry SHALL render managed-agent command paths through explicit agent scopes.

Templates for zero-or-many local managed-agent registry/fleet operations SHALL render `houmao-mgr agents global ...`.

Templates for one explicitly selected local managed-agent identity SHALL render `houmao-mgr agents single --agent-id <id> ...` or `houmao-mgr agents single --agent-name <name> ...`.

Templates for selected-agent lifecycle controls that require explicit one-agent targeting SHALL render through `houmao-mgr agents single --agent-id <id> ...` or `houmao-mgr agents single --agent-name <name> ...`.

Templates for current managed-agent operations resolved from the caller's managed tmux session SHALL render `houmao-mgr agents self ...`.

Templates for current-session `prompt`, `interrupt`, and active-surface `relaunch` SHALL render through `houmao-mgr agents self ...` when the intent is to operate on the caller's current managed tmux session.

Templates for selected-agent relaunch recovery, including stopped relaunchable-record revival and degraded/stale active-record recovery, SHALL render through `houmao-mgr agents single --agent-id <id> relaunch` or `houmao-mgr agents single --agent-name <name> relaunch`.

Templates for external-agent registry/reference onboarding SHALL render `houmao-mgr agents external ...` and SHALL NOT render lifecycle-management commands for those external runtimes.

Templates for project-owned managed-agent instances SHALL render `houmao-mgr project [--project-dir <dir>] agents ...`.

The maintained registry SHALL NOT render ambiguous root-level `houmao-mgr agents <verb>` paths for commands whose semantics require global, single, self, external, or project target ownership.

The maintained registry SHALL NOT expose public global launch templates; first-birth templates SHALL be project-scoped or internal native-agent templates.

#### Scenario: Global list template renders zero-agent query path
- **WHEN** an agent renders the managed-agent list template
- **THEN** the rendered argv represents `houmao-mgr agents global list`
- **AND THEN** it does not include `--agent-id` or `--agent-name`

#### Scenario: Single lifecycle template renders scoped selected-agent path
- **WHEN** an agent renders a selected-agent stop template for managed-agent id `agent-123`
- **THEN** the rendered argv represents `houmao-mgr agents single --agent-id agent-123 stop`
- **AND THEN** it does not represent `houmao-mgr agents stop --agent-id agent-123`

#### Scenario: Single nested template renders group-level selector
- **WHEN** an agent renders a selected-agent gateway prompt template for managed-agent name `worker-a`
- **THEN** the rendered argv starts with `houmao-mgr agents single --agent-name worker-a gateway prompt`
- **AND THEN** the nested `gateway prompt` command does not repeat `--agent-name`

#### Scenario: Self mail template renders current-session path
- **WHEN** an agent renders a current-session mail read template for message ref `msg-1`
- **THEN** the rendered argv represents `houmao-mgr agents self mail read --message-ref msg-1`
- **AND THEN** it does not include `--agent-id`, `--agent-name`, or `--current-session`

#### Scenario: Self relaunch template renders current-session path
- **WHEN** an agent renders a current-session relaunch template
- **THEN** the rendered argv represents `houmao-mgr agents self relaunch`
- **AND THEN** it does not include `--agent-id`, `--agent-name`, or `--current-session`

#### Scenario: Self prompt template renders current-session path
- **WHEN** an agent renders a current-session prompt template
- **THEN** the rendered argv starts with `houmao-mgr agents self prompt`
- **AND THEN** it does not include `--agent-id`, `--agent-name`, or `--current-session`

#### Scenario: Self lifecycle stop template is not maintained
- **WHEN** an agent lists maintained public command templates
- **THEN** the list does not include a template that renders `houmao-mgr agents self stop`
- **AND THEN** the list does not include a template that renders `houmao-mgr agents self cleanup`
- **AND THEN** selected-agent stop and cleanup remain represented through `houmao-mgr agents single --agent-id <id> ...` or `houmao-mgr agents single --agent-name <name> ...`

#### Scenario: External reference template renders external path
- **WHEN** an agent renders a remote-reference get template for imported agent `remote-reviewer`
- **THEN** the rendered argv represents `houmao-mgr agents external get --agent-name remote-reviewer`
- **AND THEN** it does not represent `houmao-mgr agents global external get --agent-name remote-reviewer`
- **AND THEN** it does not render a local lifecycle-management command for that external runtime

#### Scenario: Project agent template renders project selector
- **WHEN** an agent renders a project-agent list template with project directory `/repo`
- **THEN** the rendered argv starts with `houmao-mgr project --project-dir /repo agents list`
- **AND THEN** it does not render a global registry list command

#### Scenario: Global launch template is not maintained
- **WHEN** an agent lists maintained public command templates
- **THEN** the list does not include an `agents.global.launch` template id
- **AND THEN** project-backed birth remains represented by project-agent launch templates
