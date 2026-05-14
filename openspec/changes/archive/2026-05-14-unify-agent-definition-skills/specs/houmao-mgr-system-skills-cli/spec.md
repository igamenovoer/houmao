## ADDED Requirements

### Requirement: System-skills CLI reports unified agent-definition ownership
`houmao-mgr system-skills list`, `install`, `status`, and `uninstall` SHALL report `houmao-agent-definition` as the canonical skill for persisted agent definitions, specialists, easy profiles, explicit launch profiles, and ready-profile creation.

If `houmao-specialist-mgr` remains installable, `system-skills list` and status-oriented output SHALL distinguish it as a compatibility wrapper.

#### Scenario: List identifies canonical unified skill
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the command reports `houmao-agent-definition` as the canonical agent-definition skill
- **AND THEN** any listed `houmao-specialist-mgr` entry is identified as compatibility-only rather than a separate canonical specialist-management skill

#### Scenario: Default install does not duplicate canonical ownership
- **WHEN** an operator installs the default Houmao-owned skill selection into a target tool home
- **THEN** the resolved install list includes `houmao-agent-definition`
- **AND THEN** it does not require a second canonical specialist-management skill for the same workflows
