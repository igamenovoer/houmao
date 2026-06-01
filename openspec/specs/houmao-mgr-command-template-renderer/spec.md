# houmao-mgr-command-template-renderer Specification

## Purpose
TBD - created by archiving change add-cli-command-template-renderer. Update Purpose after archive.
## Requirements
### Requirement: `houmao-mgr internals command-templates` exposes supported command templates
`houmao-mgr` SHALL expose an internal command family shaped as:

```text
houmao-mgr internals command-templates <verb>
```

At minimum, `internals command-templates` SHALL expose:

- `list`
- `show`
- `render`

The initial template registry SHALL include stable template ids for:

- `project.easy.specialist.create`
- `project.easy.specialist.set`
- `project.easy.profile.create`
- `project.easy.profile.set`
- `project.easy.instance.launch`
- `project.agents.roles.init`
- `project.agents.roles.set`
- `project.agents.recipes.add`
- `project.agents.recipes.set`
- `project.agents.launch-profiles.add`
- `project.agents.launch-profiles.set`
- credential command families for project and plain agent-definition lanes, with tool lanes `claude`, `codex`, and `gemini`, and command verbs `add`, `set`, `login`, `list`, `get`, `rename`, and `remove`
- agent lifecycle command templates for launch, launch-profile launch, join, relaunch, cleanup session, and cleanup logs
- gateway command templates for discovery/control/TUI helpers, mail notifier status/enable/disable, and reminders list/get/create/set/remove
- mailbox command templates for shared mailbox, project mailbox, project mailbox accounts/messages, and managed-agent mailbox binding commands
- managed-agent mail fallback command templates for `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`

Every structured result emitted by this command family SHALL use the shared `houmao-mgr` output engine and SHALL support `houmao-mgr --print-json`.

The template registry SHALL NOT include skill-native loop scaffolds, workspace layout scaffolds, semantic workflow prompts, tour examples, or advanced usage patterns unless a future `houmao-mgr` command surface owns those artifacts directly.

#### Scenario: Agent lists supported templates
- **WHEN** an agent runs `houmao-mgr --print-json internals command-templates list`
- **THEN** the output includes the initial template ids
- **AND THEN** each listed template includes a short description and target command path

#### Scenario: Skill-native scaffolds are not listed as command templates
- **WHEN** an agent runs `houmao-mgr --print-json internals command-templates list`
- **THEN** the output does not include loop execplan scaffold templates, workspace layout templates, or semantic workflow prompt templates
- **AND THEN** every listed template maps to an existing `houmao-mgr` command surface

#### Scenario: Unknown template id fails clearly
- **WHEN** an agent runs `houmao-mgr --print-json internals command-templates show --id project.easy.unknown`
- **THEN** the command fails clearly
- **AND THEN** it reports that the requested template id is not registered

### Requirement: Command templates describe sparse field semantics
Each command template SHALL describe required fields, optional fields, field value types, repeatability, CLI option mappings, default action, omitted-field semantics, clear-field semantics, conflicts, and conditional requirements.

Supported field default actions SHALL include:

- `required`
- `set-if-supplied`
- `omit-to-inherit`
- `clear-only`
- `conditional`

Templates SHALL describe prompt mode and TUI/headless posture as separate fields when the target command can author either concern.

Templates SHALL NOT describe `prompt_mode=unattended` as an implied default for Codex or Claude authoring when the user did not explicitly request prompt-mode persistence.

Templates SHALL NOT describe headless posture as implied by unattended prompt mode, gateway defaults, mailbox defaults, model defaults, or reasoning defaults.

Credential templates SHALL describe tool-specific option shapes for Claude, Codex, and Gemini without duplicating credential-kind prose in packaged skills.

Gateway, mailbox, and managed-agent mail templates SHALL describe command arguments and conflicts only; HTTP payload examples and mailbox-processing workflow prompts remain owned by their skills or server/API contracts.

#### Scenario: Show reports prompt-mode omission semantics
- **WHEN** an agent runs `houmao-mgr --print-json internals command-templates show --id project.easy.profile.create`
- **THEN** the `prompt_mode` field reports the `--prompt-mode` CLI option
- **AND THEN** it reports `omit-to-inherit` or equivalent omitted semantics rather than a stored unattended default

#### Scenario: Show reports launch posture separately from prompt mode
- **WHEN** an agent runs `houmao-mgr --print-json internals command-templates show --id project.agents.launch-profiles.add`
- **THEN** launch posture fields report their own CLI options and omitted semantics
- **AND THEN** prompt mode fields do not imply those launch posture fields

#### Scenario: Show reports credential tool option shape
- **WHEN** an agent runs `houmao-mgr --print-json internals command-templates show --id project.credentials.codex.add`
- **THEN** the template reports Codex credential fields such as API key, base URL, organization id, and cached auth JSON
- **AND THEN** it does not report Claude-only or Gemini-only credential options as applicable fields

#### Scenario: Show reports gateway reminder conflicts
- **WHEN** an agent runs `houmao-mgr --print-json internals command-templates show --id agents.gateway.reminders.create`
- **THEN** the template reports the supported reminder targeting fields and scheduling fields
- **AND THEN** it reports conflicts between prompt delivery and raw key sequence delivery

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

#### Scenario: Render returns argv for a sparse easy profile intent
- **WHEN** an agent renders `project.easy.profile.create` with fields `name=reviewer-fast` and `specialist=reviewer`
- **THEN** the output argv represents `houmao-mgr project easy profile create --name reviewer-fast --specialist reviewer`
- **AND THEN** the output reports omitted optional fields instead of adding default-valued options

#### Scenario: Render does not execute the target command
- **WHEN** an agent renders `project.easy.specialist.create` with a valid sparse intent
- **THEN** the renderer returns a command proposal
- **AND THEN** no specialist is created only because the render command ran

#### Scenario: Render reports blockers for conflicting fields
- **WHEN** an agent renders a template intent that sets both `managed_header=enabled` and `managed_header=disabled`
- **THEN** the output reports a blocker for the conflicting fields
- **AND THEN** the output does not include executable argv

### Requirement: Renderer preserves omission, clear, and patch semantics
The renderer SHALL distinguish omitted fields from explicit clear requests and explicit set requests.

For create-style templates, omitted optional fields SHALL remain absent from argv so the target command's create semantics decide whether no stored value is written.

For set-style templates, omitted optional fields SHALL remain absent from argv so the target command preserves existing stored values.

Clear fields SHALL render only when the target template declares an explicit clear option for that field.

#### Scenario: Omitted prompt mode stays omitted
- **WHEN** an agent renders `project.easy.specialist.set` with fields `name=reviewer` and `model=gpt-5.4-mini`
- **THEN** the output argv includes `--name reviewer` and `--model gpt-5.4-mini`
- **AND THEN** the output argv does not include `--prompt-mode unattended`, `--prompt-mode as_is`, or `--clear-prompt-mode`

#### Scenario: Explicit clear prompt mode renders clear flag
- **WHEN** an agent renders `project.easy.specialist.set` with fields `name=reviewer` and `clear_prompt_mode=true`
- **THEN** the output argv includes `--clear-prompt-mode`
- **AND THEN** the output reports `clear_prompt_mode` as an applied field rather than an omitted default

#### Scenario: Raw profile set preserves unspecified advanced blocks
- **WHEN** an agent renders `project.agents.launch-profiles.set` with fields `name=alice` and `workdir=/repos/alice-next`
- **THEN** the output argv includes only the requested profile target and workdir mutation
- **AND THEN** the output reports that omitted prompt overlay, mailbox, managed-header, and prompt-mode fields are preserved by the target patch command

#### Scenario: Credential render keeps lane-specific fields explicit
- **WHEN** an agent renders `project.credentials.claude.add` with fields `name=main` and `api_key=sk-placeholder`
- **THEN** the output argv represents the matching `houmao-mgr project credentials claude add` command with the explicit credential fields
- **AND THEN** the output omits update, login, and non-Claude options that were not supplied

#### Scenario: Agent lifecycle render keeps posture absent when unspecified
- **WHEN** an agent renders an agent lifecycle launch template with a valid agent selector but no explicit headless or TUI posture
- **THEN** the output argv does not include headless posture flags
- **AND THEN** the output reports launch posture as omitted so the underlying launch policy resolves it

#### Scenario: Managed-agent mail fallback render keeps workflow out of scope
- **WHEN** an agent renders `agents.mail.send` with recipient, subject, and body fields
- **THEN** the output argv represents the matching `houmao-mgr agents mail send` fallback command
- **AND THEN** the renderer does not attempt to decide whether live gateway HTTP or fallback CLI is semantically preferred for the current workflow

