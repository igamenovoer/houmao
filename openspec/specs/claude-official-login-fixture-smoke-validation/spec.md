## Purpose
Define the local-only Claude `official-login` fixture contract and the reproducible smoke-validation flow for vendor login-state launches.
## Requirements

### Requirement: Repository defines one local-only `official-login` Claude auth fixture for vendor-login smoke validation

The optional Claude vendor-login smoke SHALL select an imported bundle in the external local store. It SHALL preserve `files/.credentials.json` opaquely and accept a supported companion `files/.claude.json`, including a minimized valid object. The lane SHALL NOT require `claude_state.template.json`, store auth files in the checkout, or become a prerequisite for the generic API cases.

#### Scenario: Fixture guidance describes the `official-login` local-only bundle with current filenames
- **WHEN** a maintainer reads vendor-login fixture guidance
- **THEN** it names `.credentials.json` and supported companion `.claude.json` files in an imported external bundle
- **AND THEN** it describes `claude_state.template.json` as unnecessary
- **AND THEN** it explains discovery/import without asking maintainers to populate a repository-local credential directory

#### Scenario: Maintainer can populate `official-login` from a vendor Claude config root
- **WHEN** a maintainer explicitly selects a discovered Claude login candidate for import
- **THEN** its credential JSON is copied unchanged into the external store
- **AND THEN** the supported companion state matches the current Claude projection contract
- **AND THEN** the original vendor config root remains unchanged

### Requirement: Repository provides a reproducible `official-login` Claude smoke launch flow

The smoke SHALL create a fresh external private workdir/project overlay, seed the `server-api-smoke` role, import the selected local vendor bundle through maintained credential behavior, and create a temporary specialist. It SHALL launch through `houmao-mgr project agents launch --mode headless` with unattended posture and use scoped agent stop/cleanup. It SHALL preserve native routing and require no state template.

#### Scenario: Smoke flow launches from a fresh temp workdir with a temporary project overlay
- **WHEN** a maintainer runs the vendor-login smoke with a selected imported bundle
- **THEN** it creates a fresh workdir and project overlay under the external private run root
- **AND THEN** prompt material comes from `tests/fixtures/plain-agent-def/roles/server-api-smoke/system-prompt.md`
- **AND THEN** it imports the selected bundle into that project and launches its specialist through the maintained project headless command

#### Scenario: Smoke flow proves projected vendor login-state works without a state template
- **WHEN** the selected imported bundle contains `.credentials.json` and valid minimized companion state
- **AND WHEN** the smoke launches from its fresh private project
- **THEN** the isolated Claude home uses the projected vendor login state without `claude_state.template.json`
- **AND THEN** neither DeepSeek routing nor unrelated ambient provider credentials are injected

#### Scenario: Smoke flow uses scoped selected-agent cleanup
- **WHEN** the smoke has captured the launched agent ID
- **THEN** it stops that agent with `houmao-mgr agents single --agent-id <agent_id> stop`
- **AND THEN** any session cleanup uses `houmao-mgr agents single --agent-id <agent_id> cleanup session`
- **AND THEN** it does not call retired root-level launch, stop, or cleanup commands
