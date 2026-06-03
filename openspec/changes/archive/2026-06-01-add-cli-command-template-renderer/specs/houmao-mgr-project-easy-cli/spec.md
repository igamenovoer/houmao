## ADDED Requirements

### Requirement: `project easy` authoring surfaces provide command-template entries
The CLI-owned command-template registry SHALL provide template entries for these `project easy` surfaces:

- `houmao-mgr project easy specialist create`
- `houmao-mgr project easy specialist set`
- `houmao-mgr project easy profile create`
- `houmao-mgr project easy profile set`
- `houmao-mgr project easy instance launch`

Each template entry SHALL map structured field names to the corresponding CLI options and SHALL document required fields, optional fields, clear flags, conflicts, and omitted-field semantics for that surface.

Rendering a `project easy` template SHALL produce argv that is equivalent to invoking the underlying `project easy` command directly with the same explicit options.

Profile templates SHALL include profile-owned memo seed fields because those fields are authored through `project easy profile create|set`.

#### Scenario: Easy specialist create has a template entry
- **WHEN** an agent lists command templates
- **THEN** `project.easy.specialist.create` appears as a supported template id
- **AND THEN** it maps to `houmao-mgr project easy specialist create`

#### Scenario: Easy profile set has clear-field metadata
- **WHEN** an agent shows `project.easy.profile.set`
- **THEN** the template describes supported update and clear fields for nullable launch defaults
- **AND THEN** it distinguishes omitted fields from explicit clears

#### Scenario: Easy profile create exposes memo seed fields
- **WHEN** an agent shows `project.easy.profile.create`
- **THEN** the template reports supported memo seed text, file, and directory fields
- **AND THEN** it reports conflicts between mutually exclusive memo seed sources

### Requirement: `project easy` templates preserve launch default omission
`project easy` command templates SHALL preserve the underlying CLI's sparse default behavior by omitting optional fields that are absent from render intent.

For profile and specialist create surfaces, omitted optional fields SHALL remain absent from rendered argv rather than being populated from skill-owned defaults.

For profile and specialist set surfaces, omitted optional fields SHALL remain absent from rendered argv so existing stored state is preserved.

For easy instance launch, omitted one-shot overrides SHALL remain absent from rendered argv so launch policy and stored profile/specialist state resolve the effective behavior.

Prompt mode SHALL only render when the intent explicitly sets or clears prompt mode.

Headless or TUI launch posture SHALL only render when the intent explicitly requests launch posture or a template rule can determine a required posture from supplied intent.

#### Scenario: Easy profile create omits prompt mode by default
- **WHEN** an agent renders `project.easy.profile.create` with only `name=reviewer-fast` and `specialist=reviewer`
- **THEN** the rendered argv does not include `--prompt-mode`
- **AND THEN** the rendered output reports prompt mode as omitted/inherited

#### Scenario: Easy specialist set preserves existing prompt mode
- **WHEN** an agent renders `project.easy.specialist.set` with only `name=reviewer` and `model=gpt-5.4-mini`
- **THEN** the rendered argv does not include `--prompt-mode` or `--clear-prompt-mode`
- **AND THEN** the target specialist's stored prompt mode is preserved by the patch command

#### Scenario: Easy launch keeps one-shot posture absent when unspecified
- **WHEN** an agent renders `project.easy.instance.launch` for specialist `reviewer` and instance `reviewer-1`
- **AND WHEN** the render intent does not include headless or TUI posture
- **THEN** the rendered argv does not include `--headless`
- **AND THEN** the eventual launch remains governed by stored state and launch policy rather than a skill-owned posture default
