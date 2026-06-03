## ADDED Requirements

### Requirement: CLI reference omits the removed LLM Wiki utility system skill
The CLI reference page `docs/reference/cli/system-skills.md` SHALL NOT describe `houmao-utils-llm-wiki` as a current packaged Houmao-owned system skill, current set member, install example, status result, or uninstall target.

#### Scenario: Reader cannot install the removed utility from documented examples
- **WHEN** a reader checks install examples in `docs/reference/cli/system-skills.md`
- **THEN** no example uses `--skill houmao-utils-llm-wiki`
- **AND THEN** no current inventory or set listing includes `houmao-utils-llm-wiki`

## REMOVED Requirements

### Requirement: CLI reference documents the LLM Wiki utility system skill
**Reason**: `houmao-utils-llm-wiki` is no longer a packaged Houmao-owned system skill.

**Migration**: Remove the LLM Wiki utility row, explicit install examples, and named-set/default-selection prose from the system-skills CLI reference.
