## MODIFIED Requirements

### Requirement: Functional profiles remain development-only skill data
Functional areas and coverage profiles SHALL remain committed Markdown resources of `houmao-dev-behavior-testing`. They SHALL NOT add a runtime dependency, packaged system skill, or admin or agent pack member.

#### Scenario: Runtime skill manifest is inspected
- **WHEN** the packaged system-skill manifest and actor packs are resolved
- **THEN** behavior-testing functional areas and coverage profiles do not appear as installable runtime skills
