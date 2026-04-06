## MODIFIED Requirements

### Requirement: User-facing source directories

When the system consumes a filesystem-backed reusable agent-definition source tree, it SHALL organize that source under a stable on-disk layout rooted at `agents/`.

At minimum, that filesystem-backed source layout SHALL include:

- `agents/skills/<skill>/SKILL.md`
- `agents/roles/<role>/system-prompt.md`
- `agents/presets/<preset>.yaml`
- `agents/tools/<tool>/adapter.yaml`
- `agents/tools/<tool>/setups/<setup>/...`
- `agents/tools/<tool>/auth/<auth>/...`

Project-local catalog-backed overlays MAY persist canonical semantic relationships outside that directory layout, provided they still resolve to the same canonical parsed or domain semantics before construction.

User-facing reusable launch metadata for filesystem-backed trees SHALL continue to live in presets plus tool-scoped setup and auth directories rather than in a separate recipe plus blueprint layer.

#### Scenario: Developer locates source files in a filesystem-backed source tree

- **WHEN** a developer needs to add or modify reusable agent-definition sources in a filesystem-backed tree
- **THEN** skill packages SHALL live under `agents/skills/`
- **AND THEN** role prompts SHALL live under `agents/roles/`
- **AND THEN** launchable preset files SHALL live under `agents/presets/`
- **AND THEN** tool-specific setup and auth material SHALL live under `agents/tools/`

### Requirement: Agent preset schema is minimal and extensible

Agent presets SHALL include only fields required by current behavior: selected role, selected tool, selected setup, selected skills, optional default auth, optional launch settings, optional mailbox settings, and optional `extra`.

The system SHALL NOT require build-time `default_agent_name` or other duplicated launch identity fields in preset files.

If present, preset `launch` SHALL be an object containing optional `prompt_mode`, optional `overrides`, and optional `env_records`.

`launch.overrides`, when present, SHALL use the existing launch-overrides shape of optional `args` and optional `tool_params`.

Allowed `launch.prompt_mode` values SHALL be `unattended` and `as_is`.

`launch.env_records`, when present, SHALL be a mapping of non-empty env names to string values representing persistent specialist-owned launch env records.

`launch.env_records` SHALL remain distinct from credential env:

- env names that belong to the selected tool adapter's auth-env allowlist SHALL be rejected
- Houmao-owned reserved env names SHALL be rejected

Unknown top-level preset fields SHALL be rejected. Non-core extension data SHALL live under `extra` rather than through pre-allocated unused top-level schema fields.

The preset name SHALL be derived from the preset filename stem. The preset file SHALL require top-level `role`, `tool`, and `setup`, and it SHALL NOT require a duplicated top-level `name`.

#### Scenario: Minimal preset omits duplicated preset-name fields

- **WHEN** a developer authors `agents/presets/researcher-codex-default.yaml`
- **THEN** the preset SHALL provide `role`, `tool`, and `setup` as top-level fields
- **AND THEN** the preset MAY omit `name` and `default_agent_name`
- **AND THEN** the system SHALL resolve the preset name from the filename stem

#### Scenario: Launch settings use one explicit schema

- **WHEN** a developer authors preset-owned launch behavior
- **THEN** `prompt_mode` SHALL appear under `launch.prompt_mode`
- **AND THEN** `launch.prompt_mode` SHALL use only `unattended` or `as_is`
- **AND THEN** any preset-owned launch overrides SHALL appear under `launch.overrides`
- **AND THEN** persistent specialist env records SHALL appear under `launch.env_records`
- **AND THEN** `launch.overrides` SHALL use only the supported `args` and `tool_params` sections

#### Scenario: Specialist env record using a credential-owned env name is rejected

- **WHEN** a preset declares `launch.env_records.OPENAI_API_KEY`
- **AND WHEN** the selected tool adapter owns `OPENAI_API_KEY` through its auth-env allowlist
- **THEN** preset validation SHALL fail explicitly
- **AND THEN** the error SHALL identify that `OPENAI_API_KEY` belongs to credential env rather than persistent specialist env records

#### Scenario: Non-core preset extensions live under extra

- **WHEN** a consumer needs secret-free subsystem-specific preset metadata outside the core schema
- **THEN** that metadata SHALL be stored under `extra`
- **AND THEN** the core preset resolution path SHALL NOT depend on unsupported top-level extension fields
- **AND THEN** preserved gateway defaults, when needed for migrated blueprint behavior, SHALL live under `extra.gateway`

#### Scenario: Unknown top-level preset field fails validation

- **WHEN** a preset file declares an unsupported top-level field such as legacy `config_profile`
- **THEN** preset loading SHALL fail explicitly
- **AND THEN** the error SHALL direct authors toward the supported core fields and `extra`

### Requirement: Tracked canonical presets for live role variants

The repository SHALL provide tracked, declarative, secret-free presets under `agents/presets/` for the live role variants that the repo documents and verifies.

At minimum, the tracked preset set SHALL include:

- `agents/presets/gpu-kernel-coder-claude-default.yaml`
- `agents/presets/gpu-kernel-coder-codex-default.yaml`
- `agents/presets/gpu-kernel-coder-codex-yunwu-openai.yaml`

Each tracked preset SHALL select one role, one tool, selected skills, one setup, and optional default auth by identifier only and SHALL NOT embed secret material.

#### Scenario: Developer can locate tracked preset variants for the GPU demo role

- **WHEN** a developer needs to inspect or update the supported launch variants for `gpu-kernel-coder`
- **THEN** the repo SHALL contain tracked named presets under `agents/presets/` for the documented tool and setup variants
- **AND THEN** those presets SHALL remain declarative and secret-free

## REMOVED Requirements

### Requirement: Path-derived agent presets
**Reason**: Preset identity is no longer derived from role-scoped path nesting. Named presets now store `role`, `tool`, and `setup` inside the preset file and derive only the preset name from the file name.
**Migration**: Move canonical preset files from `agents/roles/<role>/presets/<tool>/<setup>.yaml` to `agents/presets/<name>.yaml`, add top-level `role`, `tool`, and `setup`, and update callers to use the new named preset path.
