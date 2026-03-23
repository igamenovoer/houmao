## MODIFIED Requirements

### Requirement: Launcher home directory anchors CAO state and process HOME
The launcher SHALL support an optional `home_dir` setting that is applied to the launched `cao-server` process as its `HOME` value.

This setting exists to choose the CAO state/profile-store root under `HOME/.aws/cli-agent-orchestrator/`. The chosen `home_dir` MUST remain writable because CAO writes its own state there.

The launcher SHALL NOT define or document a repo-owned rule that CAO session workdirs must live under `home_dir` or the user home tree. Workdir acceptance for later CAO-backed sessions belongs to the installed CAO server behavior, while the launcher owns only the launched process `HOME` and state-root configuration.

#### Scenario: Launcher overrides HOME when home_dir is configured
- **WHEN** the launcher starts `cao-server` with a configured `home_dir` value `H`
- **THEN** the launched process environment sets `HOME=H`

#### Scenario: Missing home_dir is rejected
- **WHEN** the launcher is asked to start `cao-server` with a configured `home_dir` that does not exist
- **THEN** the launcher fails fast with an explicit configuration error

#### Scenario: Launcher guidance does not require session workdirs under home_dir
- **WHEN** a developer follows repo-owned launcher docs or examples
- **THEN** those docs describe `home_dir` as the CAO state/profile-store anchor
- **AND THEN** they do not instruct the developer to place session workdirs under `home_dir` solely because of a repo-owned launcher rule
