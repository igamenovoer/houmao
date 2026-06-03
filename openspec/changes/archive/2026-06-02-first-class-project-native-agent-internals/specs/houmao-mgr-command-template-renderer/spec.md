## MODIFIED Requirements

### Requirement: `houmao-mgr internals command-templates` exposes supported command templates
`houmao-mgr` SHALL expose an internal command family shaped as:

```text
houmao-mgr internals command-templates <verb>
```

At minimum, `internals command-templates` SHALL expose:

- `list`
- `show`
- `render`

The maintained template registry SHALL include stable template ids for:

- `project.specialist.create`
- `project.specialist.set`
- `project.profile.create`
- `project.profile.set`
- project-scoped managed-agent lifecycle command templates for launch/list/get/stop and related maintained lifecycle verbs
- `internals.native-agent.roles.init`
- `internals.native-agent.roles.set`
- `internals.native-agent.recipes.add`
- `internals.native-agent.recipes.set`
- `internals.native-agent.launch-dossiers.add`
- `internals.native-agent.launch-dossiers.set`
- credential command families for project credential lanes, with tool lanes `claude`, `codex`, and `gemini`, and command verbs `add`, `set`, `login`, `list`, `get`, `rename`, and `remove`
- agent lifecycle command templates for non-project live-agent control where still maintained
- gateway command templates for discovery/control/TUI helpers, mail notifier status/enable/disable, and reminders list/get/create/set/remove
- mailbox command templates for shared mailbox, project mailbox, project mailbox accounts/messages, and managed-agent mailbox binding commands
- managed-agent mail fallback command templates for `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`

Every structured result emitted by this command family SHALL use the shared `houmao-mgr` output engine and SHALL support `houmao-mgr --print-json`.

The template registry SHALL NOT include skill-native loop scaffolds, workspace layout scaffolds, semantic workflow prompts, tour examples, or advanced usage patterns unless a future `houmao-mgr` command surface owns those artifacts directly.

#### Scenario: Agent lists supported templates
- **WHEN** an agent runs `houmao-mgr --print-json internals command-templates list`
- **THEN** the output includes promoted project specialist/profile template ids and native-agent internals template ids
- **AND THEN** each listed template includes a short description and target command path

#### Scenario: Old easy and project-agents ids are not maintained public ids
- **WHEN** an agent runs `houmao-mgr --print-json internals command-templates list`
- **THEN** the maintained public ids do not include `project.easy.specialist.create`, `project.easy.profile.create`, or `project.agents.launch-profiles.add`
- **AND THEN** equivalent maintained templates use `project.specialist.*`, `project.profile.*`, or `internals.native-agent.launch-dossiers.*`

#### Scenario: Skill-native scaffolds are not listed as command templates
- **WHEN** an agent runs `houmao-mgr --print-json internals command-templates list`
- **THEN** the output does not include loop execplan scaffold templates, workspace layout templates, or semantic workflow prompt templates
- **AND THEN** every listed template maps to an existing `houmao-mgr` command surface

### Requirement: Renderer converts sparse intent into non-executing argv
`houmao-mgr internals command-templates render --id <template-id>` SHALL accept a structured JSON intent with a `fields` mapping and optional render context.

The renderer SHALL return structured output containing at least:

- `template_id`
- `argv`
- `command`
- `normalized_intent`
- `applied_fields`
- `omitted_fields`
- `warnings`
- `blockers`

The renderer SHALL NOT execute the rendered target command.

When no blockers exist, `argv` SHALL contain the exact target command and arguments that a caller can execute.

When blockers exist, the renderer SHALL report the blockers and SHALL NOT return an executable `argv`.

#### Scenario: Render returns argv for a sparse project profile intent
- **WHEN** an agent renders `project.profile.create` with fields `name=reviewer-fast` and `specialist=reviewer`
- **THEN** the output argv represents `houmao-mgr project profile create --name reviewer-fast --specialist reviewer`
- **AND THEN** the output reports omitted optional fields instead of adding default-valued options

#### Scenario: Render returns argv for a native launch dossier intent
- **WHEN** an agent renders `internals.native-agent.launch-dossiers.add` with fields `native_agent_root=/tmp/native`, `name=reviewer-native`, and `recipe=reviewer-codex`
- **THEN** the output argv represents the matching `houmao-mgr internals native-agent launch-dossiers add` command
- **AND THEN** the output uses launch dossier terminology rather than launch profile terminology

#### Scenario: Render does not execute the target command
- **WHEN** an agent renders `project.specialist.create` with a valid sparse intent
- **THEN** the renderer returns a command proposal
- **AND THEN** no specialist is created only because the render command ran
