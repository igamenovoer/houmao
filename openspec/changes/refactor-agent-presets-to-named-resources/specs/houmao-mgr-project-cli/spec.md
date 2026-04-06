## MODIFIED Requirements

### Requirement: Maintained project-local source creation flows bootstrap the active overlay on demand
Maintained `houmao-mgr project agents ...` commands that create or update project-local tool, auth, role, or preset state SHALL resolve the active overlay through the shared ensure-or-bootstrap project-aware resolver instead of requiring a previously initialized overlay.

When no active project overlay exists for the caller and no stronger overlay selection override applies, these commands SHALL ensure the selected overlay exists before writing project-local state.

At minimum, this requirement SHALL apply to:

- `houmao-mgr project agents tools <tool> setups add`
- `houmao-mgr project agents tools <tool> auth add`
- `houmao-mgr project agents tools <tool> auth set`
- `houmao-mgr project agents roles init`
- `houmao-mgr project agents roles set`
- `houmao-mgr project agents presets add`
- `houmao-mgr project agents presets set`

#### Scenario: Tool auth add bootstraps the missing overlay on demand
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project agents tools codex auth add --name personal --api-key sk-test`
- **THEN** the command ensures `<cwd>/.houmao` exists before writing the auth bundle
- **AND THEN** the resulting auth bundle is stored under that active project overlay

#### Scenario: Role init uses the env-selected overlay when bootstrapping
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` does not exist
- **AND WHEN** an operator runs `houmao-mgr project agents roles init --name reviewer`
- **THEN** the command ensures `/tmp/ci-overlay` exists before creating the role
- **AND THEN** the created role root is stored under `/tmp/ci-overlay/agents/roles/reviewer`

### Requirement: Maintained project-local inspection and existing-state flows remain non-creating
Maintained `houmao-mgr project agents ...` commands that inspect existing project-local source content or remove existing project-local state SHALL resolve overlay selection through the shared non-creating project-aware resolver.

When no active project overlay exists for the caller and no stronger overlay selection override applies, these commands SHALL fail clearly without bootstrapping the selected or would-bootstrap overlay root.

At minimum, this requirement SHALL apply to:

- `houmao-mgr project agents tools <tool> get`
- `houmao-mgr project agents tools <tool> setups list`
- `houmao-mgr project agents tools <tool> setups get`
- `houmao-mgr project agents tools <tool> setups remove`
- `houmao-mgr project agents tools <tool> auth list`
- `houmao-mgr project agents tools <tool> auth get`
- `houmao-mgr project agents tools <tool> auth remove`
- `houmao-mgr project agents roles list`
- `houmao-mgr project agents roles get`
- `houmao-mgr project agents roles remove`
- `houmao-mgr project agents presets list`
- `houmao-mgr project agents presets get`
- `houmao-mgr project agents presets remove`

#### Scenario: Tool get fails clearly without bootstrapping a missing overlay
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project agents tools codex get`
- **THEN** the command fails clearly because no project overlay was discovered for the current invocation
- **AND THEN** it does not create `<cwd>/.houmao` as a side effect of that inspection command

#### Scenario: Preset remove does not create an empty overlay
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project agents presets remove --name reviewer-codex-default`
- **THEN** the command fails clearly before attempting removal
- **AND THEN** it does not bootstrap a new project overlay only to report missing existing state
