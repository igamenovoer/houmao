## ADDED Requirements

### Requirement: Config drafts expose only minimal intent holes
Each config draft SHALL expose fewer specifiable fields than the underlying Houmao data model and maintained project subcommands.

A draft id SHALL bind selected model fields to fixed values. Fixed values MAY be ordinary domain defaults or draft-specific non-default choices. Callers SHALL NOT supply fixed values in the draft intent.

Each initial draft SHALL accept only its declared minimal required intent fields:

- `project.easy.specialist`: `name`, `tool`, and `credential`
- `project.easy.profile`: `name`, `specialist`, and `credential`
- `project.agents.launch-profile`: `name`, `recipe`, and `credential`

Fields from the full data model that are not declared as draft intent fields SHALL be rejected as unsupported fields. Users who need full model coverage SHALL use maintained project subcommands directly instead of config drafts.

#### Scenario: Config draft inventory reports minimal required holes
- **WHEN** an agent runs `houmao-mgr --print-json internals config-drafts list`
- **THEN** `project.easy.specialist` reports required intent keys `name`, `tool`, and `credential`
- **AND THEN** `project.easy.profile` reports required intent keys `name`, `specialist`, and `credential`
- **AND THEN** `project.agents.launch-profile` reports required intent keys `name`, `recipe`, and `credential`

#### Scenario: Hidden full-model field is rejected
- **WHEN** an agent generates `project.easy.profile` with fields `name`, `specialist`, `credential`, and `model`
- **THEN** the command fails with an unsupported-field diagnostic for `model`
- **AND THEN** the command does not silently copy `model` into the generated YAML

#### Scenario: Fixed draft field is rejected when supplied
- **WHEN** an agent generates `project.agents.launch-profile` with fields `name`, `recipe`, `credential`, and `profile_lane`
- **THEN** the command fails with an unsupported-field diagnostic for `profile_lane`
- **AND THEN** the draft id remains the only source of the generated profile lane

### Requirement: Config drafts require credential references
Each initial config draft SHALL require a `credential` intent field. The credential field SHALL be interpreted as a credential/auth reference in the generated config draft.

Config drafts SHALL NOT accept credential material fields such as API keys, base URLs, OAuth tokens, auth JSON files, or vendor-specific login files. Credential material creation and mutation SHALL remain in maintained credential/project commands.

#### Scenario: Specialist draft requires credential
- **WHEN** an agent generates `project.easy.specialist` with fields `name` and `tool` but without `credential`
- **THEN** the command fails with a missing-input diagnostic for `credential`
- **AND THEN** it does not derive a credential name from the specialist name

#### Scenario: Profile draft renders credential reference
- **WHEN** an agent generates `project.easy.profile` with fields `name=reviewer-fast`, `specialist=reviewer`, and `credential=reviewer-creds`
- **THEN** the generated YAML records a specialist-backed easy profile
- **AND THEN** the generated YAML records `reviewer-creds` as the profile's auth or credential reference

#### Scenario: Credential material is rejected
- **WHEN** an agent generates `project.easy.specialist` with fields `name`, `tool`, `credential`, and `api_key`
- **THEN** the command fails with an unsupported-field diagnostic for `api_key`
- **AND THEN** it directs the caller back to credential/project commands by behavior rather than by accepting secret material in the draft

### Requirement: Initial config drafts generate opinionated minimal YAML
The initial config drafts SHALL generate concrete YAML documents from fixed draft values and required intent fields only.

`project.easy.specialist` SHALL generate a high-level specialist draft with fixed `config_kind: project.easy.specialist`, caller-supplied `name`, caller-supplied `tool`, caller-supplied credential reference, and draft-owned fixed launch/setup values needed for the easy specialist path.

`project.easy.profile` SHALL generate a specialist-backed easy profile draft with caller-supplied `name`, fixed `profile_lane: easy_profile`, fixed `source.kind: specialist`, caller-supplied `source.name` from `specialist`, and caller-supplied credential/auth reference.

`project.agents.launch-profile` SHALL generate a recipe-backed raw launch-profile draft with caller-supplied `name`, fixed `profile_lane: launch_profile`, fixed `source.kind: recipe`, caller-supplied `source.name` from `recipe`, and caller-supplied credential/auth reference.

Generated YAML SHALL NOT include hidden optional override sections such as model, reasoning, env, mailbox, skills, system skills, posture, gateway port, managed header, prompt overlay, gateway mail notifier appendix, memo seed, relaunch chat-session policy, or credential material unless a later spec explicitly adds a narrower draft that exposes those fields.

#### Scenario: Specialist draft is minimal and opinionated
- **WHEN** an agent generates `project.easy.specialist` with fields `name=reviewer`, `tool=codex`, and `credential=reviewer-creds`
- **THEN** the generated YAML includes `config_kind: project.easy.specialist`, `name: reviewer`, `tool: codex`, and a credential reference to `reviewer-creds`
- **AND THEN** the generated YAML does not include model, env, mailbox, skill, prompt, or credential material sections

#### Scenario: Easy profile draft is minimal and opinionated
- **WHEN** an agent generates `project.easy.profile` with fields `name=reviewer-fast`, `specialist=reviewer`, and `credential=reviewer-creds`
- **THEN** the generated YAML includes `profile_lane: easy_profile`
- **AND THEN** the generated YAML includes `source.kind: specialist` and `source.name: reviewer`
- **AND THEN** the generated YAML does not include hidden launch override sections beyond the required credential/auth reference

#### Scenario: Raw launch profile draft is minimal and opinionated
- **WHEN** an agent generates `project.agents.launch-profile` with fields `name=reviewer-raw`, `recipe=reviewer-codex`, and `credential=reviewer-creds`
- **THEN** the generated YAML includes `profile_lane: launch_profile`
- **AND THEN** the generated YAML includes `source.kind: recipe` and `source.name: reviewer-codex`
- **AND THEN** the generated YAML does not include hidden launch override sections beyond the required credential/auth reference
