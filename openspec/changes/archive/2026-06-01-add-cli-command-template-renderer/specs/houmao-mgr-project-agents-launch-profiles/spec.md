## ADDED Requirements

### Requirement: Launch-profile authoring surfaces provide command-template entries
The CLI-owned command-template registry SHALL provide template entries for these low-level recipe-backed launch-profile surfaces:

- `houmao-mgr project agents launch-profiles add`
- `houmao-mgr project agents launch-profiles set`

Each template entry SHALL map structured field names to the corresponding CLI options and SHALL document required fields, optional fields, clear flags, conflicts, create-vs-patch semantics, and omitted-field semantics for that surface.

Rendering a launch-profile template SHALL produce argv that is equivalent to invoking the underlying `project agents launch-profiles` command directly with the same explicit options.

#### Scenario: Launch-profile add has required source metadata
- **WHEN** an agent shows `project.agents.launch-profiles.add`
- **THEN** the template identifies `name` and `recipe` as required fields
- **AND THEN** it identifies optional launch defaults separately from those required fields

#### Scenario: Launch-profile set has patch metadata
- **WHEN** an agent shows `project.agents.launch-profiles.set`
- **THEN** the template reports that omitted update fields preserve existing stored launch-profile content
- **AND THEN** it reports clear flags for nullable fields that the set command can clear

### Requirement: Launch-profile templates preserve create and patch omission semantics
The launch-profile templates SHALL distinguish create-style omission from patch-style omission.

For `project.agents.launch-profiles.add`, omitted optional fields SHALL remain absent from rendered argv so the add command writes no stored value for those fields or clears them during confirmed same-lane replacement according to existing add semantics.

For `project.agents.launch-profiles.set`, omitted optional fields SHALL remain absent from rendered argv so the set command preserves existing stored values and advanced blocks.

Prompt mode SHALL only render when the intent explicitly sets prompt mode or explicitly clears prompt mode on the set surface.

Launch posture SHALL only render when the intent explicitly requests a TUI/headless posture or a template rule can determine a required posture from supplied intent.

#### Scenario: Launch-profile add omits default-sensitive fields
- **WHEN** an agent renders `project.agents.launch-profiles.add` with fields `name=alice` and `recipe=reviewer-codex-default`
- **THEN** the rendered argv includes only the required profile and recipe fields
- **AND THEN** it does not include prompt-mode, headless, managed-header, mailbox, prompt-overlay, model, or reasoning options

#### Scenario: Launch-profile set omits prompt mode during unrelated patch
- **WHEN** an agent renders `project.agents.launch-profiles.set` with fields `name=alice` and `workdir=/repos/alice-next`
- **THEN** the rendered argv includes the workdir update
- **AND THEN** it does not include prompt-mode set or clear options

#### Scenario: Explicit launch posture renders posture option
- **WHEN** an agent renders a launch-profile template with an explicit headless posture request
- **THEN** the rendered argv includes the matching launch posture option
- **AND THEN** the output reports the posture field as applied rather than inferred
