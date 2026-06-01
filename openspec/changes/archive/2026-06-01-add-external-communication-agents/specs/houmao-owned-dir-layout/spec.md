## ADDED Requirements

### Requirement: Shared registry root may contain external-agent discovery metadata
The shared registry root SHALL be allowed to contain external communication-only managed-agent discovery records in addition to local lifecycle-managed live-agent records.

External-agent records SHALL remain registry-owned locator metadata. They SHALL NOT contain mutable runtime session state, launcher-managed provider home state, mailbox contents, gateway process state, or task artifacts.

The default external-agent registry collection SHALL remain under the shared registry root and SHALL NOT be relocated under project runtime, mailbox, memory, or workspace directories by default.

#### Scenario: External import stores only locator metadata
- **WHEN** an operator registers remote agent `james` as external local name `remote-james`
- **THEN** the system writes only discovery metadata under the shared registry root
- **AND THEN** remote manifests, remote tmux state, remote gateway process state, mailbox contents, and task artifacts are not copied into the local registry root

#### Scenario: External records stay in the shared registry zone
- **WHEN** maintained local Houmao commands run in a project context without a registry override
- **AND WHEN** an external communication-only agent is registered
- **THEN** the external record is stored beneath the effective shared registry root
- **AND THEN** the record is not stored beneath the active project overlay's runtime, mailbox, memory, easy, or workspace-local directories
