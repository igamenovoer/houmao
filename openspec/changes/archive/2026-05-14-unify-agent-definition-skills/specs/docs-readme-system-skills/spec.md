## ADDED Requirements

### Requirement: README system-skill prose describes unified agent definition
README system-skill prose SHALL describe `houmao-agent-definition` as the canonical skill for low-level roles and recipes, explicit launch profiles, specialists, easy profiles, and ready-profile creation.

README prose SHALL NOT present `houmao-specialist-mgr` as the current independent canonical specialist-management skill after the unification.

#### Scenario: README user-control inventory is not split by specialist manager
- **WHEN** a reader checks the README system-skill inventory
- **THEN** the reader sees `houmao-agent-definition` covering both low-level and easy agent-definition workflows
- **AND THEN** the README does not require the reader to choose `houmao-specialist-mgr` for ordinary specialist or easy-profile authoring
