## ADDED Requirements

### Requirement: `houmao-create-specialist` explains filesystem mailbox behavior on specialist-backed easy launch
When the packaged `houmao-specialist-mgr` skill describes `project easy instance launch` with filesystem mailbox support, the launch guidance SHALL distinguish launch-time mailbox flags from profile-create declarative mailbox fields.

At minimum, that launch guidance SHALL state that `project easy instance launch` does not accept profile-create declarative mailbox fields such as `--mail-address`, `--mail-principal-id`, `--mail-base-url`, `--mail-jmap-url`, or `--mail-management-url`.

The launch guidance SHALL state that the supported launch-time filesystem mailbox inputs are `--mail-transport filesystem`, `--mail-root`, and optional `--mail-account-dir`.

The launch guidance SHALL state that the managed-agent instance name seeds the ordinary filesystem mailbox identity for launch-owned mailbox bootstrap when mailbox support is enabled and no explicit private mailbox directory override changes the storage path.

The launch guidance SHALL explain that `--mail-account-dir` is a private filesystem mailbox directory that is symlinked into the shared mailbox root and therefore MUST live outside that shared root.

The launch guidance SHALL warn that manual preregistration of the same address under the same mailbox root can collide with the launch's safe mailbox bootstrap for that instance.

#### Scenario: Specialist launch guidance excludes profile-only mailbox fields
- **WHEN** an agent reads the specialist-manager launch action for mailbox-enabled `project easy instance launch`
- **THEN** the skill states that launch-time filesystem mailbox support uses only the documented launch flags
- **AND THEN** it does not present `--mail-address` or `--mail-principal-id` as supported `project easy instance launch` flags

#### Scenario: Specialist launch guidance explains private mailbox directory placement
- **WHEN** an agent reads the specialist-manager launch action for `--mail-account-dir`
- **THEN** the skill explains that the path is a private mailbox directory symlinked into the shared root
- **AND THEN** it states that the private mailbox directory must live outside the shared mailbox root

#### Scenario: Specialist launch guidance warns about preregistering the same address
- **WHEN** an agent reads the specialist-manager launch action for launch-owned filesystem mailbox binding
- **AND WHEN** the intended mailbox address follows the ordinary managed-agent identity pattern for the same mailbox root
- **THEN** the skill warns that preregistering that same address can make safe launch bootstrap fail
- **AND THEN** it tells the reader to let launch own that address unless they are intentionally using a different manual-registration or late-binding lane
