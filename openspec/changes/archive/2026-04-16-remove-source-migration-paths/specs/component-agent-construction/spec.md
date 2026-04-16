## ADDED Requirements

### Requirement: Agent construction source parsing is current-shape only
Maintained agent construction paths SHALL accept the current preset, tool-adapter, setup, auth, and launch-overrides source shapes only.

The builder SHALL NOT treat legacy recipe documents as preset-compatible construction inputs.

The builder CLI SHALL NOT preserve hidden legacy aliases for current construction inputs. At minimum, the maintained CLI surface SHALL require:

- `--preset` instead of `--recipe`,
- `--setup` instead of `--config-profile`,
- `--auth` instead of `--cred-profile`.

Tool adapter parsing SHALL require current field names. At minimum, adapter parsing SHALL require `setup_projection` and `auth_projection` and SHALL NOT accept `config_projection` or `credential_projection` as aliases.

#### Scenario: Current preset construction succeeds
- **WHEN** a developer constructs a brain from a current preset and current tool adapter fields
- **THEN** brain construction resolves the preset, setup, auth, skills, and launch overrides from current source shapes
- **AND THEN** no legacy recipe or alias path is used

#### Scenario: Legacy recipe file is rejected
- **WHEN** a developer supplies an old recipe-shaped file that lacks the current preset contract
- **THEN** brain construction rejects that file explicitly
- **AND THEN** it does not convert the old recipe into a preset-shaped compatibility object

#### Scenario: Hidden legacy build flags are unsupported
- **WHEN** a developer invokes the builder with `--recipe`, `--config-profile`, or `--cred-profile`
- **THEN** argument parsing fails because those aliases are not part of the maintained build surface
- **AND THEN** the developer must use the current `--preset`, `--setup`, and `--auth` inputs

#### Scenario: Tool adapter legacy projection aliases are rejected
- **WHEN** a tool adapter declares `config_projection` or `credential_projection` instead of the current projection fields
- **THEN** adapter parsing fails explicitly
- **AND THEN** the adapter must be rewritten with current field names before construction proceeds
