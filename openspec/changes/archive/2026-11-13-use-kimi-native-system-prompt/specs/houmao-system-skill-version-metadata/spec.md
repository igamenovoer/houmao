## ADDED Requirements

### Requirement: Non-collection assets remain outside the system-skill version contract
The top-level version contract SHALL exclude legacy system skills, generated execplan skills, and project-authored skills.

The presence or absence of `houmao_version` in those excluded assets SHALL NOT affect system-skill doctor results for the static public collection. Provider-native system-prompt files SHALL be inspected through brain provenance rather than parsed as skills.

#### Scenario: Project-authored skill is installed
- **WHEN** doctor inspects a managed agent home containing a project-authored skill outside the static public collection
- **THEN** it does not require or compare `houmao_version` on that project-authored skill
- **AND THEN** it evaluates only the expected standalone static pack roots

#### Scenario: Managed Kimi native prompt is present
- **WHEN** doctor inspects a managed Kimi home containing `SYSTEM.md`
- **THEN** it does not treat the file as a system skill or require skill release metadata on it
- **AND THEN** system-prompt integrity remains the responsibility of brain provenance inspection

## REMOVED Requirements

### Requirement: Non-collection skills remain outside the version contract
**Reason**: The old requirement named the deleted managed auto-prompt skill as a version-contract category.

**Migration**: Apply version checks only to the static public system-skill collection and inspect native prompt files through brain provenance.
