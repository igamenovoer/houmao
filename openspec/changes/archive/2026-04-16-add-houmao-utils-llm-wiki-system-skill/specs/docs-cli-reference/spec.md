## ADDED Requirements

### Requirement: CLI reference documents the LLM Wiki utility system skill
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-utils-llm-wiki` as a packaged Houmao-owned system skill.

The reference SHALL document the `utils` named set and SHALL show explicit installation examples for both `--skill-set utils` and `--skill houmao-utils-llm-wiki`.

The reference SHALL state that `utils` is not included in managed launch, managed join, or CLI-default selections.

The reference SHALL include `houmao-utils-llm-wiki` anywhere it enumerates the current skill inventory.

#### Scenario: Reader sees the utility skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-utils-llm-wiki` as a packaged Houmao-owned skill
- **AND THEN** the page lists `utils` as a named set

#### Scenario: Reader can install the utility skill from documented examples
- **WHEN** a reader checks the install examples in `docs/reference/cli/system-skills.md`
- **THEN** the examples include `--skill-set utils` or `--skill houmao-utils-llm-wiki`
- **AND THEN** the surrounding text states that the utility skill is explicit-only

#### Scenario: CLI default documentation excludes the utility set
- **WHEN** a reader checks managed-launch, managed-join, or CLI-default selection lists in CLI reference docs
- **THEN** those default-selection lists do not include `utils`
- **AND THEN** they do not imply `houmao-utils-llm-wiki` is installed by default
