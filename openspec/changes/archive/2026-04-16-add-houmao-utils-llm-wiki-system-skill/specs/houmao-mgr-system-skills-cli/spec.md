## ADDED Requirements

### Requirement: `houmao-mgr system-skills` surfaces the LLM Wiki utility skill and utils set
`houmao-mgr system-skills` SHALL use the packaged catalog inventory and named sets when reporting, installing, inspecting, and removing `houmao-utils-llm-wiki`.

When `system-skills install` resolves an explicit `utils` set selection, the reported installed skill names and later `system-skills status` output SHALL include `houmao-utils-llm-wiki` whenever that install completed successfully.

When `system-skills install` resolves the packaged CLI-default selection, the resolved installed skill names SHALL NOT include `houmao-utils-llm-wiki`.

`system-skills uninstall` SHALL remove `houmao-utils-llm-wiki` when that current catalog-known skill path exists in the resolved home.

#### Scenario: Operator lists the utility skill and named set
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the output includes `houmao-utils-llm-wiki` in the current skill inventory
- **AND THEN** the output includes the `utils` named set
- **AND THEN** the managed-launch, managed-join, and CLI-default set lists do not include `utils`

#### Scenario: Operator installs the utility set explicitly
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --skill-set utils`
- **THEN** the resolved skill list includes `houmao-utils-llm-wiki`
- **AND THEN** the skill is projected into the Codex home under `skills/houmao-utils-llm-wiki/`

#### Scenario: Operator installs the utility skill explicitly
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex --skill houmao-utils-llm-wiki`
- **THEN** the resolved skill list includes `houmao-utils-llm-wiki`
- **AND THEN** the skill is projected into the Codex home under `skills/houmao-utils-llm-wiki/`

#### Scenario: CLI-default install omits the utility skill
- **WHEN** an operator runs `houmao-mgr system-skills install --tool codex`
- **THEN** the resolved CLI-default skill list does not include `houmao-utils-llm-wiki`

#### Scenario: Uninstall removes an installed utility skill path
- **WHEN** a Codex home contains `skills/houmao-utils-llm-wiki/`
- **AND WHEN** an operator runs `houmao-mgr system-skills uninstall --tool codex --home <home>`
- **THEN** the command removes `skills/houmao-utils-llm-wiki/`
