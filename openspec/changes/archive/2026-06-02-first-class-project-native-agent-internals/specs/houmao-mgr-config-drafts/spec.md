## MODIFIED Requirements

### Requirement: `houmao-mgr internals config-drafts` exposes concise config draft generators
`houmao-mgr` SHALL expose an internal command family shaped as:

```text
houmao-mgr internals config-drafts <verb>
```

At minimum, `internals config-drafts` SHALL expose:

- `list`
- `generate`

The draft registry SHALL include stable draft ids for:

- `project.specialist`
- `project.profile`
- `internals.native-agent.launch-dossier`

`list` SHALL return a compact inventory containing draft ids, short descriptions, config kinds, and required intent keys. It SHALL NOT return full CLI option catalogs, command-template field metadata, omitted-field prose, or target argv.

`generate --id <draft-id>` SHALL accept a structured JSON intent with a `fields` mapping and SHALL emit a YAML config draft for the selected draft id without mutating project or native-agent state.

#### Scenario: Agent lists supported config drafts
- **WHEN** an agent runs `houmao-mgr --print-json internals config-drafts list`
- **THEN** the output includes `project.specialist`, `project.profile`, and `internals.native-agent.launch-dossier`
- **AND THEN** each listed item contains concise draft metadata rather than command-template fields or target argv

#### Scenario: Agent generates a project profile YAML draft
- **WHEN** an agent runs `houmao-mgr internals config-drafts generate --id project.profile --intent '{"fields":{"name":"reviewer-fast","specialist":"reviewer","credential":"reviewer-creds"}}'`
- **THEN** the command emits a YAML document for a specialist-backed project profile
- **AND THEN** the command does not create or update a project profile only because draft generation ran

#### Scenario: Missing required input fails clearly
- **WHEN** an agent generates `project.profile` without a profile name
- **THEN** the command fails clearly with a missing-input diagnostic
- **AND THEN** it does not emit a misleading partial profile draft as though it were ready to use

### Requirement: Config drafts expose only minimal intent holes
Each config draft SHALL expose fewer specifiable fields than the underlying Houmao data model and maintained project or native-agent subcommands.

A draft id SHALL bind selected model fields to fixed values. Fixed values MAY be ordinary domain defaults or draft-specific non-default choices. Callers SHALL NOT supply fixed values in the draft intent.

Each initial draft SHALL accept only its declared minimal required intent fields:

- `project.specialist`: `name`, `tool`, and `credential`
- `project.profile`: `name`, `specialist`, and `credential`
- `internals.native-agent.launch-dossier`: `name`, `recipe`, and `credential`

Fields from the full data model that are not declared as draft intent fields SHALL be rejected as unsupported fields. Users who need full model coverage SHALL use maintained project or native-agent subcommands directly instead of config drafts.

#### Scenario: Config draft inventory reports minimal required holes
- **WHEN** an agent runs `houmao-mgr --print-json internals config-drafts list`
- **THEN** `project.specialist` reports required intent keys `name`, `tool`, and `credential`
- **AND THEN** `project.profile` reports required intent keys `name`, `specialist`, and `credential`
- **AND THEN** `internals.native-agent.launch-dossier` reports required intent keys `name`, `recipe`, and `credential`

#### Scenario: Hidden full-model field is rejected
- **WHEN** an agent generates `project.profile` with fields `name`, `specialist`, `credential`, and `model`
- **THEN** the command fails with an unsupported-field diagnostic for `model`
- **AND THEN** the command does not silently copy `model` into the generated YAML

### Requirement: Initial config drafts generate opinionated minimal YAML
The initial config drafts SHALL generate concrete YAML documents from fixed draft values and required intent fields only.

`project.specialist` SHALL generate a high-level specialist draft with fixed `config_kind: project.specialist`, caller-supplied `name`, caller-supplied `tool`, caller-supplied credential reference, and draft-owned fixed launch/setup values needed for the project specialist path.

`project.profile` SHALL generate a specialist-backed project profile draft with caller-supplied `name`, fixed project-profile lane, fixed `source.kind: specialist`, caller-supplied `source.name` from `specialist`, and caller-supplied credential/auth reference.

`internals.native-agent.launch-dossier` SHALL generate a recipe-backed native launch dossier draft with caller-supplied `name`, fixed native launch-dossier kind, fixed `source.kind: recipe`, caller-supplied `source.name` from `recipe`, and caller-supplied credential/auth reference.

Generated YAML SHALL NOT include hidden optional override sections such as model, reasoning, env, mailbox, skills, system skills, posture, gateway port, managed header, prompt overlay, gateway mail notifier appendix, memo seed, relaunch chat-session policy, or credential material unless a later spec explicitly adds a narrower draft that exposes those fields.

#### Scenario: Specialist draft is minimal and opinionated
- **WHEN** an agent generates `project.specialist` with fields `name=reviewer`, `tool=codex`, and `credential=reviewer-creds`
- **THEN** the generated YAML includes `config_kind: project.specialist`, `name: reviewer`, `tool: codex`, and a credential reference to `reviewer-creds`
- **AND THEN** the generated YAML does not include model, env, mailbox, skill, prompt, or credential material sections

#### Scenario: Launch dossier draft is minimal and opinionated
- **WHEN** an agent generates `internals.native-agent.launch-dossier` with fields `name=reviewer-native`, `recipe=reviewer-codex`, and `credential=reviewer-creds`
- **THEN** the generated YAML identifies the document as a native launch dossier
- **AND THEN** the generated YAML includes `source.kind: recipe` and `source.name: reviewer-codex`
- **AND THEN** the generated YAML does not include hidden launch override sections beyond the required credential/auth reference
