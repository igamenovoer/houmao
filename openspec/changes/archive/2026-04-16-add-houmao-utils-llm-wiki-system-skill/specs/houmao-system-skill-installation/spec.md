## ADDED Requirements

### Requirement: Packaged system-skill catalog includes explicit LLM Wiki utility guidance
The packaged current-system-skill catalog SHALL include `houmao-utils-llm-wiki` as a current installable Houmao-owned skill.

The packaged skill asset SHALL live at `src/houmao/agents/assets/system_skills/houmao-utils-llm-wiki/`, and its catalog `asset_subpath` SHALL be `houmao-utils-llm-wiki`.

The packaged catalog SHALL include a dedicated `utils` named set containing `houmao-utils-llm-wiki`.

The packaged catalog's fixed `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` selections SHALL NOT include the `utils` set.

#### Scenario: Maintainer inspects the utility skill catalog entry
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-utils-llm-wiki`
- **AND THEN** the `utils` named set resolves to `houmao-utils-llm-wiki`
- **AND THEN** `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` do not include `utils`

#### Scenario: Explicit utility selection resolves the LLM Wiki skill
- **WHEN** Houmao resolves an explicit `utils` system-skill set selection
- **THEN** the resolved skill list includes `houmao-utils-llm-wiki`
- **AND THEN** the skill projects through the same shared installer contract as other current Houmao-owned skills

### Requirement: LLM Wiki utility skill ships the all-in-one payload
The packaged `houmao-utils-llm-wiki` asset SHALL include the adapted all-in-one LLM Wiki skill instructions, references, scripts, subskills, and bundled viewer source.

The packaged skill SHALL keep helper command examples in `python3` form.

The packaged skill SHALL NOT preserve upstream attribution text.

#### Scenario: Maintainer inspects the packaged utility asset
- **WHEN** a maintainer inspects `src/houmao/agents/assets/system_skills/houmao-utils-llm-wiki/`
- **THEN** it contains `SKILL.md`, `references/`, `scripts/`, `subskills/`, and `viewer/`
- **AND THEN** helper examples use `python3`
- **AND THEN** the packaged skill text does not preserve upstream attribution text
