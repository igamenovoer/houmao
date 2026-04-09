## ADDED Requirements

### Requirement: Effective launch prompt uses structured Houmao system-prompt layout
Before backend-specific role injection begins, the runtime SHALL render one effective launch prompt rooted at `<houmao_system_prompt>`.

When managed-header policy resolves to enabled, the rendered prompt SHALL contain a `<managed_header>` section.

When non-header prompt content exists, the rendered prompt SHALL contain a `<prompt_body>` section.

Within `<prompt_body>`, the runtime SHALL render the following sections in order when they participate in the launch:
1. `<role_prompt>`
2. `<launch_profile_overlay>`
3. `<launch_appendix>`

When launch-profile overlay mode is `replace`, the runtime SHALL omit `<role_prompt>` from `<prompt_body>`.

The runtime SHALL treat the rendered prompt as the single effective launch prompt for backend-specific role injection and SHALL NOT require provider-specific parsing of the section tags.

#### Scenario: Managed launch renders header, overlay, and appendix as one structured prompt
- **WHEN** a managed launch resolves enabled managed-header policy
- **AND WHEN** the launch uses a source role prompt, an append-mode launch-profile overlay, and a launch-owned appendix
- **THEN** the effective launch prompt is rooted at `<houmao_system_prompt>`
- **AND THEN** the rendered prompt contains `<managed_header>` followed by `<prompt_body>` whose sections appear in the order `<role_prompt>`, `<launch_profile_overlay>`, `<launch_appendix>`

#### Scenario: Replace overlay omits the source role section
- **WHEN** a launch resolves launch-profile overlay mode `replace`
- **AND WHEN** the operator also supplies a launch-owned appendix
- **THEN** `<prompt_body>` contains `<launch_profile_overlay>` followed by `<launch_appendix>`
- **AND THEN** the runtime does not also render `<role_prompt>` for that launch

### Requirement: Structured launch prompt layout is persisted for relaunch and compatibility
For launches created after this capability is implemented, brain construction SHALL persist both the final rendered effective launch prompt text and secret-free `houmao_system_prompt_layout` metadata sufficient to identify the structured prompt layout version and rendered sections.

For those launches, relaunch, resume, and compatibility-generated prompt construction SHALL reuse the persisted rendered prompt contract rather than inventing a separate prompt layout.

For older manifests that do not persist `houmao_system_prompt_layout`, relaunch SHALL remain valid and MAY fall back to legacy prompt recomposition rules.

#### Scenario: New build persists structured prompt layout metadata
- **WHEN** a managed launch is built after the structured prompt-layout capability ships
- **THEN** the build manifest stores the final rendered effective launch prompt text
- **AND THEN** the build manifest also stores secret-free `houmao_system_prompt_layout` metadata that describes the rendered structured prompt sections

#### Scenario: Older manifest relaunch remains valid without structured layout metadata
- **WHEN** a relaunch targets an older manifest that lacks `houmao_system_prompt_layout`
- **THEN** relaunch still succeeds using the maintained fallback prompt-resolution behavior
- **AND THEN** the runtime does not require retroactive layout metadata in order to relaunch that session
