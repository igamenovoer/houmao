## MODIFIED Requirements

### Requirement: README system-skill prose describes unified agent definition
README system-skill prose SHALL describe `houmao-agent-definition` as the canonical skill for low-level roles and recipes, `raw-profiles`, specialists, easy `profiles`, and `create-agent-fast-forward`.

README prose SHALL NOT present `houmao-specialist-mgr` as the current independent canonical specialist-management skill after the unification.

#### Scenario: README user-control inventory is not split by specialist manager
- **WHEN** a reader checks the README system-skill inventory
- **THEN** the reader sees `houmao-agent-definition` covering both low-level and easy agent-definition workflows
- **AND THEN** the README does not require the reader to choose `houmao-specialist-mgr` for ordinary specialist or easy-profile authoring

#### Scenario: README names default profile terminology
- **WHEN** a reader checks the README system-skill inventory for profile authoring
- **THEN** easy-profile authoring is named as `profiles`
- **AND THEN** low-level recipe-backed profiles are named as `raw-profiles`
