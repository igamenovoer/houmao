# Spec Delta

## ADDED Requirements

### Requirement: Shared routines help reports exact eighteen-child count and post-3.0.0 routes
`houmao-shared-routines/commands/help.md` SHALL replace the stale `"sixteen"` count with `"eighteen"` (`18`) parent-scoped children, and `SKILL.md` `When to Route Here` descriptions SHALL distinguish `request` vs `prompt`, `houmao-cccc`, `open-browser`, `mailbox online`, and usage inspection.

#### Scenario: Collection-wide help matches manifest eighteen-child inventory
- **WHEN** a caller runs `houmao-shared-routines->help()` for collection-wide help
- **THEN** `commands/help.md` states eighteen (`18`) parent-scoped children matching `manifest.toml` and the `SKILL.md` route table
- **AND THEN** route descriptions in `SKILL.md` reflect post-3.0.0 capabilities without copying child descriptions verbatim

### Requirement: Shared routines deduplicates actor-frame prose across entrypoint and reference
`houmao-shared-routines` SHALL remove duplicated actor-selection explanation between `SKILL.md` `## Actor Selection` and `references/actor-frame.md` so each detail lives in one authoritative place per `imsight-agent-skill-handling`.

#### Scenario: Actor frame definition lives in one canonical place
- **WHEN** a reviewer inspects `houmao-shared-routines/SKILL.md` and `references/actor-frame.md`
- **THEN** `SKILL.md` states concise actor-selection steps and links `references/actor-frame.md` for the six-field frame contract without repeating the full block

### Requirement: Shared routines preserves explicit activation, frame validation, and selective child loading
`houmao-shared-routines` SHALL preserve explicit-only activation, help before actor verification or child loading, immutable inherited six-field frame validation, `as-agent` fresh `agents self identity`, selective single-child `SKILL-MAIN.md` loading, `specialist-mgr` alias, and join transition rules.

#### Scenario: Selective child loading never scans sibling directories
- **WHEN** `houmao-shared-routines` resolves a valid route for the verified actor frame
- **THEN** it loads only the selected `subskills/<logical-id>/SKILL-MAIN.md` and its internal resources
- **AND THEN** it keeps `| <route> |` and `"When to Route Here"` compliant with `system_skill_manifest.py`
