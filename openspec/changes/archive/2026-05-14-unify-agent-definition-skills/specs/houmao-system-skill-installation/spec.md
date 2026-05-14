## ADDED Requirements

### Requirement: Packaged catalog marks unified agent definition as canonical
The packaged current-system-skill catalog SHALL expose `houmao-agent-definition` as the canonical installable skill for pre-launch agent-definition, specialist, easy-profile, explicit launch-profile, and ready-profile workflows.

The catalog SHALL NOT require default installations to include both canonical `houmao-agent-definition` and a separate canonical specialist-management skill.

If `houmao-specialist-mgr` remains packaged, the catalog SHALL mark or document it as a compatibility skill rather than as the canonical specialist-management surface.

#### Scenario: Maintainer inspects current skill inventory
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** `houmao-agent-definition` is the canonical current skill for specialist and profile authoring
- **AND THEN** `houmao-specialist-mgr`, if present, is not described as an independent canonical owner of those workflows
