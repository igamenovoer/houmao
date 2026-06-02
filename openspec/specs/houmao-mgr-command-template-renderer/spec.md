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
- credential command families for project credential lanes and internal native-agent credential lanes, with tool lanes `claude`, `codex`, and `gemini`, and command verbs `add`, `set`, `login`, `list`, `get`, `rename`, and `remove`
- `internals.native-agent.brain.build`
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

#### Scenario: Unknown template id fails clearly
- **WHEN** an agent runs `houmao-mgr --print-json internals command-templates show --id project.unknown`
- **THEN** the command fails clearly
- **AND THEN** it reports that the requested template id is not registered

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
- **WHEN** an agent runs `houmao-mgr --print-json internals command-templates show --id project.profile.create`
- **THEN** the `prompt_mode` field reports the `--prompt-mode` CLI option
- **AND THEN** it reports `omit-to-inherit` or equivalent omitted semantics rather than a stored unattended default

#### Scenario: Show reports launch posture separately from prompt mode
- **WHEN** an agent runs `houmao-mgr --print-json internals command-templates show --id internals.native-agent.launch-dossiers.add`
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
- **WHEN** an agent renders `project.specialist.set` with fields `name=reviewer` and `model=gpt-5.4-mini`
- **THEN** the output argv includes `--name reviewer` and `--model gpt-5.4-mini`
- **AND THEN** the output argv does not include `--prompt-mode unattended`, `--prompt-mode as_is`, or `--clear-prompt-mode`

#### Scenario: Explicit clear prompt mode renders clear flag
- **WHEN** an agent renders `project.specialist.set` with fields `name=reviewer` and `clear_prompt_mode=true`
- **THEN** the output argv includes `--clear-prompt-mode`
- **AND THEN** the output reports `clear_prompt_mode` as an applied field rather than an omitted default

#### Scenario: Launch dossier set preserves unspecified advanced blocks
- **WHEN** an agent renders `internals.native-agent.launch-dossiers.set` with fields `name=alice` and `workdir=/repos/alice-next`
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
- **WHEN** an agent renders `agents.single.mail.send` with recipient, subject, body, and one selected-agent selector
- **THEN** the output argv represents the matching scoped `houmao-mgr agents single ... mail send` fallback command
- **AND THEN** the renderer does not attempt to decide whether live gateway HTTP or fallback CLI is semantically preferred for the current workflow

### Requirement: Command templates are declared in code-first family modules
The command-template registry SHALL keep Python as the runtime source of truth while organizing template declarations into family-specific modules under a dedicated command-template package.

The modular registry SHALL preserve the existing public template ids, target command paths, field payloads, conflict behavior, omission behavior, and render behavior unless a future change explicitly modifies those contracts.

The registry assembly SHALL detect duplicate template ids before exposing the registry to `list`, `show`, `render`, or export callers.

#### Scenario: Registry loads from family modules without changing ids
- **WHEN** `houmao-mgr --print-json internals command-templates list` is executed after the modular split
- **THEN** the output includes the same covered command-template ids as before the split
- **AND THEN** each listed template still maps to an existing `houmao-mgr` command surface

#### Scenario: Duplicate template ids fail before rendering
- **WHEN** two family modules declare the same command-template id
- **THEN** registry assembly fails clearly before returning a template registry
- **AND THEN** the failure names the duplicate template id

### Requirement: Template datamodel remains frozen and typed
Command templates, template fields, and field conflicts SHALL be represented by frozen typed Python dataclasses or equivalent immutable typed models.

Template models SHALL continue to fix the supported field actions, value types, target argv shape, conflict shape, and required-alternative shape before template data reaches the renderer.

Family modules MAY use Python helper functions to generate repetitive concrete templates, but they SHALL return concrete typed template objects to the registry.

#### Scenario: Family helper returns concrete templates
- **WHEN** a generated family such as credentials or mailbox contributes templates to the registry
- **THEN** the registry receives concrete command-template objects with resolved ids, target argv, fields, conflicts, and required alternatives
- **AND THEN** callers do not need to understand the family helper that generated them

#### Scenario: Invalid typed model is rejected
- **WHEN** a template family attempts to register a template whose field value type or field action is outside the supported typed set
- **THEN** the invalid declaration fails during normal Python validation, type checking, or registry validation
- **AND THEN** no partial registry is exposed to command-template callers

### Requirement: Command templates export deterministic YAML views
The command-template package SHALL provide functions that export one command template or the complete registry as deterministic YAML derived from the same structured payload used by `show`.

YAML export SHALL be a generated view of the code-first registry and SHALL NOT become the runtime source of truth.

The YAML export SHALL preserve field order within a template, sort complete-registry output deterministically by template id, and include a trailing newline.

#### Scenario: Single-template YAML export matches show payload
- **WHEN** a caller exports `project.agents.launch` as YAML
- **THEN** the parsed YAML contains the same template id, target argv, field metadata, conflicts, required alternatives, notes, and family metadata as `houmao-mgr --print-json internals command-templates show --id project.agents.launch`
- **AND THEN** the YAML output is deterministic across repeated exports

#### Scenario: Complete-registry YAML export is deterministic
- **WHEN** a caller exports all command templates as YAML
- **THEN** the output contains every registered command template exactly once
- **AND THEN** templates are ordered deterministically by template id

### Requirement: Internal CLI exposes YAML export for command templates
`houmao-mgr internals command-templates` SHALL expose an export command for writing YAML views of the code-first command-template registry.

The export command SHALL support exporting a single template id to stdout or to a specified YAML file path.

The export command SHALL support exporting the complete registry to stdout or to a specified output directory containing one YAML file per template id.

The export command SHALL fail clearly when the caller supplies neither a template id nor an all-templates selection, or when the caller supplies conflicting output modes.

#### Scenario: Agent exports one template to stdout
- **WHEN** an agent runs `houmao-mgr internals command-templates export --id project.profile.create`
- **THEN** stdout contains a YAML document for that one command template
- **AND THEN** the command does not execute the target command represented by the template

#### Scenario: Maintainer exports all templates to files
- **WHEN** a maintainer runs `houmao-mgr internals command-templates export --all --output-dir /tmp/templates`
- **THEN** Houmao writes one deterministic `.yaml` file per registered command-template id under `/tmp/templates`
- **AND THEN** each file contains a YAML view generated from the code-first registry

#### Scenario: Export rejects ambiguous selection
- **WHEN** a caller runs `houmao-mgr internals command-templates export` without `--id` or `--all`
- **THEN** the command fails clearly
- **AND THEN** the error explains that the caller must select one template or all templates

### Requirement: Command templates remain argv-oriented and do not own config drafts
`houmao-mgr internals command-templates` SHALL remain the internal surface for inspecting and rendering maintained `houmao-mgr` command argv.

Command templates SHALL NOT be treated as the primary agent-facing contract for project configuration YAML authoring when a matching `houmao-mgr internals config-drafts` draft id exists.

The command-template registry MAY continue to include entries for the underlying project commands so existing argv-rendering workflows keep working, but packaged skills SHALL prefer config drafts for draft-document authoring and command templates for executable command construction.

#### Scenario: Matching config draft supersedes command-template schema inspection for config authoring
- **WHEN** an agent needs a specialist-backed project profile config document
- **AND WHEN** `internals config-drafts` provides `project.profile`
- **THEN** maintained skill guidance uses the config draft surface for the YAML authoring shape
- **AND THEN** it does not require `internals command-templates show --id project.profile.create` only to discover the full CLI option schema

#### Scenario: Command templates still render executable commands
- **WHEN** an agent needs to print or run a maintained `houmao-mgr` command that is not represented as a config document
- **THEN** the command-template renderer remains available for sparse intent to argv rendering
- **AND THEN** the config-draft surface does not need to mirror every command-oriented template id

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
