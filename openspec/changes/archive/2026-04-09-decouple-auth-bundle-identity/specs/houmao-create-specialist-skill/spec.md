## ADDED Requirements

### Requirement: `houmao-create-specialist` treats credential defaults as display-name defaults only
The create action within the packaged `houmao-specialist-mgr` skill SHALL treat `--credential` as the operator-facing auth display name used for selection or creation rather than as an implied storage-path key.

When the user omits `--credential`, the skill MAY continue using `<specialist-name>-creds` as the documented display-name default without implying that the resulting auth profile must use the same basename for managed content or compatibility projection storage.

The create guidance SHALL NOT describe auth rename, auth storage paths, or auth directory basenames as something the operator must coordinate manually for specialist creation.

#### Scenario: Installed skill presents the default credential as a display-name default
- **WHEN** an agent follows the create path inside the installed `houmao-specialist-mgr` skill
- **THEN** the skill states that `--credential` defaults to `<specialist-name>-creds`
- **AND THEN** it does not imply that the auth profile's storage path basename must equal that display name

#### Scenario: Existing auth profile display name still satisfies specialist create
- **WHEN** the current prompt or recent conversation establishes specialist name and tool
- **AND WHEN** the skill confirms that an auth profile with the intended display name already exists for that tool
- **THEN** the skill allows specialist creation to proceed without re-entering auth inputs
- **AND THEN** it does not require the agent to inspect or reason about the auth profile's opaque storage path
