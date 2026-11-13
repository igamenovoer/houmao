## MODIFIED Requirements

### Requirement: Development testing skills remain outside runtime packs
Neither `houmao-dev-tui-testing` nor `houmao-dev-behavior-testing` SHALL be declared in the public system-skill manifest or a runtime actor pack.

#### Scenario: Runtime catalog is inspected after the rename
- **WHEN** the packaged system-skill manifest is loaded
- **THEN** it contains the same six standalone public roots as before this change
- **AND THEN** it contains neither development testing skill
