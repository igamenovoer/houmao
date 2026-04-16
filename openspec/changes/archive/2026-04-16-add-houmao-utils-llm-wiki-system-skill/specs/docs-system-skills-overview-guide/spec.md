## ADDED Requirements

### Requirement: System-skills overview guide includes the LLM Wiki utility skill
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL list `houmao-utils-llm-wiki` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe the skill as a general utility for building and maintaining persistent Markdown LLM Wiki knowledge bases with scaffold, ingest, compile, query, lint, audit, and local viewer workflows.

The guide SHALL place `houmao-utils-llm-wiki` in a utility group or equivalent section distinct from managed-agent lifecycle, messaging, gateway, mailbox, memory, project authoring, and loop-control skills.

The guide SHALL explain that the `utils` set is explicit-only and not included in managed launch, managed join, or CLI-default install selections.

#### Scenario: Reader finds the utility skill in the overview
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** they find `houmao-utils-llm-wiki` in the packaged skill overview
- **AND THEN** the description frames it as a knowledge-base utility rather than a managed-agent control skill

#### Scenario: Reader sees explicit-only utility default behavior
- **WHEN** a reader checks the overview guide's named-set or default-selection explanation
- **THEN** it lists `utils` as a named set containing `houmao-utils-llm-wiki`
- **AND THEN** it explains that default selections do not include `utils`
