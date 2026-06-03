## ADDED Requirements

### Requirement: `project easy` stores managed system-skill policy for specialists and easy profiles
`houmao-mgr project easy specialist create` and `houmao-mgr project easy specialist set` SHALL accept options for configuring managed system-skill policy on the specialist's generated recipe launch payload.

`houmao-mgr project easy profile create` and `houmao-mgr project easy profile set` SHALL accept options for configuring managed system-skill policy on specialist-backed easy profiles.

The accepted options SHALL include repeatable `--system-skill-set <set>`, repeatable `--system-skill <skill>`, `--system-skills-mode <mode>`, `--no-system-skills`, and the patch-only clear option `--clear-system-skills`.

For specialist commands, omitted policy SHALL mean the managed-launch default selection. For easy-profile commands, omitted policy SHALL mean inherit from the source specialist.

When a specialist command receives one or more system-skill selectors without an explicit mode, it SHALL store additive mode. When an easy-profile command receives one or more system-skill selectors without an explicit mode, it SHALL store additive mode over the inherited source policy.

#### Scenario: Specialist create stores additive utility skill policy
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --api-key sk-test --system-skill houmao-utils-llm-wiki`
- **THEN** the persisted specialist records managed system-skill policy as additive
- **AND THEN** the generated compatibility recipe records `houmao-utils-llm-wiki` under `launch.system_skills`

#### Scenario: Specialist set clears stored system-skill policy
- **WHEN** specialist `researcher` stores additive system-skill policy
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --clear-system-skills`
- **THEN** the specialist no longer stores explicit managed system-skill policy
- **AND THEN** later launches from the specialist use the packaged managed-launch default selection

#### Scenario: Easy profile create stores additive profile policy
- **WHEN** specialist `researcher` already exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name researcher-wiki --specialist researcher --system-skill houmao-utils-llm-wiki`
- **THEN** the easy profile stores additive managed system-skill policy
- **AND THEN** launches from that profile include the source specialist policy plus `houmao-utils-llm-wiki`

#### Scenario: Easy profile set disables managed system skills
- **WHEN** easy profile `researcher-minimal` already exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name researcher-minimal --no-system-skills`
- **THEN** the easy profile stores disabled managed system-skill policy
- **AND THEN** future launches from that profile install no current Houmao-owned system skills

#### Scenario: Invalid easy system-skill name fails clearly
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --api-key sk-test --system-skill not-a-skill`
- **THEN** the command fails before storing the specialist
- **AND THEN** the error identifies `not-a-skill` as an unknown Houmao system skill
