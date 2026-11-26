# Spec Delta

## MODIFIED Requirements

### Requirement: Shared routines preserves explicit activation, frame validation, and selective child loading
`houmao-shared-routines` SHALL preserve explicit-only activation, help before actor verification or child loading, immutable inherited six-field frame validation, `as-agent` fresh `agents self identity`, selective single-child `SKILL-MAIN.md` loading, and the `specialist-mgr` alias.

#### Scenario: Selective child loading never scans sibling directories
- **WHEN** `houmao-shared-routines` resolves a valid route for the verified actor frame
- **THEN** it loads only the selected `subskills/<logical-id>/SKILL-MAIN.md` and its internal resources
- **AND THEN** it keeps `| <route> |` and `"When to Route Here"` compliant with `system_skill_manifest.py`
