# Spec Delta

## ADDED Requirements

### Requirement: README mentions the managed prompt header for launched agents

The README section that summarizes the operator-facing capabilities of a managed agent SHALL include one short note explaining that managed launches prepend a Houmao-owned prompt header by default, and SHALL link to the new managed prompt header reference page (`docs/reference/run-phase/managed-prompt-header.md`).

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The note SHALL state that the header is opt-out via `--no-managed-header` on the launch surfaces and is persisted in stored launch profiles, deferring the full explanation to the linked reference page.

#### Scenario: Reader notices the managed prompt header from the README

- **WHEN** a reader scans the README summary of managed-agent capabilities
- **THEN** they find one short note explaining that managed launches prepend a Houmao-owned prompt header by default
- **AND THEN** the note links to `docs/reference/run-phase/managed-prompt-header.md`
- **AND THEN** the note states that the header is opt-out via `--no-managed-header`

## MODIFIED Requirements

### Requirement: README distinguishes external and managed pack defaults
The README SHALL state that explicit external-home installation defaults to the admin pack, while managed launch, rebuild, and relaunch default to the agent pack.

It SHALL state that the admin welcome and entrypoint install atomically and that no default installs both actors. It SHALL distinguish catalog-backed system-skill packs from provider-native role-prompt files created by brain construction and SHALL contain no managed auto-skill category.

#### Scenario: Reader compares two homes
- **WHEN** a reader compares a human-operated CLI-agent home with a Houmao-managed home
- **THEN** the README identifies the admin pack for the first and the agent pack for the second
- **AND THEN** it does not describe provider-native prompt files as skills or pack members

## REMOVED Requirements

### Requirement: README mentions the managed prompt header in the join/launch outcome
**Reason**: The join outcome no longer exists.
**Migration**: The README keeps the managed prompt header guidance for launched agents.
