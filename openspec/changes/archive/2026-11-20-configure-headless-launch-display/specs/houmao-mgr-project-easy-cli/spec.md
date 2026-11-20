# Project CLI Delta

## ADDED Requirements

### Requirement: Project profiles store optional headless display settings

`project profile create` and `set` SHALL accept `--headless-display-style` (`plain`, `json`, `fancy`) and `--headless-display-detail` (`concise`, `detail`). Saved values SHALL appear under `defaults.posture` as `headless_display_style` and `headless_display_detail` in profile inspection and the profile projection.

#### Scenario: An operator saves display settings on a project profile

- **WHEN** an operator creates a specialist-backed project profile with `--headless-display-style fancy --headless-display-detail detail`
- **THEN** the stored profile, `project profile get`, and the projected launch profile show the two selected values

#### Scenario: An existing profile has no saved display settings

- **WHEN** an operator inspects a project profile that has never set a display field
- **THEN** the missing field stays absent from the stored posture and its projection

### Requirement: Project profile updates edit display fields independently

`project profile set` SHALL update each supplied display field and support `--clear-headless-display-style` and `--clear-headless-display-detail`. An omitted field SHALL retain its stored value on patch. A same-field set and clear SHALL fail before mutation. Explicit profile replacement SHALL use create semantics for both fields.

#### Scenario: An operator clears one saved field

- **WHEN** a profile saves style `fancy` and detail `detail` and the operator runs `project profile set --name worker --clear-headless-display-detail`
- **THEN** the command removes only `headless_display_detail` and keeps `headless_display_style` and the other stored posture

#### Scenario: A display-only patch changes one field

- **WHEN** the operator supplies only `--headless-display-style json` as the requested update
- **THEN** the patch succeeds and preserves the stored detail

#### Scenario: An operator sets and clears the same display field

- **WHEN** `project profile set` supplies a display option and its matching clear option
- **THEN** it rejects the conflicting flags before changing the profile or its projection

#### Scenario: The operator replaces a same-name profile

- **WHEN** `project profile create --yes` replaces a specialist-backed profile and omits its prior style or detail
- **THEN** the replacement leaves that omitted field absent from stored defaults

### Requirement: Project launch resolves headless display settings per field

`project agents launch` SHALL accept the same display options for `--specialist` and `--profile`. Each field SHALL resolve from the direct flag, saved project-profile value, or its built-in default, in that order. The defaults SHALL be `plain` and `concise`. Direct options SHALL apply to the launched instance without rewriting the profile.

#### Scenario: A one-shot style override inherits the saved detail

- **WHEN** a headless project profile stores style `fancy` and detail `detail` and `project agents launch --profile worker` supplies `--headless-display-style json`
- **THEN** the launched instance uses `json` and `detail`
- **AND THEN** the profile retains `fancy` and `detail` for a future launch

#### Scenario: An omitted field falls back independently

- **WHEN** a headless launch selects a profile or specialist with no saved detail and supplies no one-shot detail
- **THEN** it uses `concise` and resolves style independently

#### Scenario: A direct specialist launch configures the pane

- **WHEN** `project agents launch --specialist` supplies display options in headless mode
- **THEN** the instance uses the supplied display values

### Requirement: Project launch checks display settings against the resolved mode

Project launch SHALL reject any direct or saved display setting when the effective mode is `tui`, `service`, or `web`. It SHALL validate authored field values and report incompatible or invalid settings during preflight, before project projection, runtime home preparation, or takeover. The execution owner SHALL apply the same check on routed launches.

#### Scenario: A launch changes the resolved mode

- **WHEN** a saved profile contains display options and the user resolves the launch to a non-headless mode, including by overriding the stored headless mode
- **THEN** preflight identifies the display setting and the effective mode and rejects the launch before runtime preparation

#### Scenario: A non-headless launch explicitly selects a display default

- **WHEN** the user supplies `--headless-display-style plain` or `--headless-display-detail concise` for a non-headless launch
- **THEN** the command rejects the supplied display setting

#### Scenario: A direct headless mode selection enables saved display controls

- **WHEN** a selected profile stores display settings and the direct mode flag resolves the launch to a supported headless backend
- **THEN** preflight accepts the settings and the launch resolves the style and detail for that backend

#### Scenario: A stored value is invalid

- **WHEN** headless launch reads a saved style or detail outside the supported values
- **THEN** it reports the invalid field during preflight

#### Scenario: The execution owner rejects an incompatible display selection

- **WHEN** a delegated launch reaches an owner and its resolved mode is incompatible with a configured display setting
- **THEN** the owner returns a determinate preflight rejection with the mode and display diagnostic
