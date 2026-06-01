## ADDED Requirements

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
- **WHEN** a caller exports `project.easy.instance.launch` as YAML
- **THEN** the parsed YAML contains the same template id, target argv, field metadata, conflicts, required alternatives, notes, and family metadata as `houmao-mgr --print-json internals command-templates show --id project.easy.instance.launch`
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
- **WHEN** an agent runs `houmao-mgr internals command-templates export --id project.easy.profile.create`
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
