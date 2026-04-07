## ADDED Requirements

### Requirement: Easy-specialist guide documents easy-lane managed-header controls
The easy-specialists guide SHALL document the managed-header controls that affect:

- `project easy profile create`
- `project easy instance launch`

The page SHALL explain:
- that easy-profile creation can store managed-header policy,
- that easy-instance launch can force-enable or disable the managed header for one launch,
- that the one-shot easy-instance override does not rewrite the stored easy profile.

#### Scenario: Reader finds managed-header controls on easy profile create and easy instance launch
- **WHEN** a reader checks the easy-lane operator workflow
- **THEN** the page documents the managed-header create-time profile control and the one-shot easy-instance launch override
- **AND THEN** the page explains how those controls interact for profile-backed easy launch
