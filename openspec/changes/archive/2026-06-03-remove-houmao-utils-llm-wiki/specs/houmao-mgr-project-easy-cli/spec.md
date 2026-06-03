## MODIFIED Requirements

### Requirement: `project` stores managed system-skill policy for specialists and project profiles
`houmao-mgr project specialist create` and `houmao-mgr project specialist set` SHALL accept options for configuring managed system-skill policy on the specialist's generated recipe launch payload.

`houmao-mgr project profile create` and `houmao-mgr project profile set` SHALL accept options for configuring managed system-skill policy on specialist-backed project profiles.

The accepted options SHALL include repeatable `--system-skill-set <set>`, repeatable `--system-skill <skill>`, `--system-skills-mode <mode>`, `--no-system-skills`, and the patch-only clear option `--clear-system-skills`.

For specialist commands, omitted policy SHALL mean the managed-launch default selection. For project-profile commands, omitted policy SHALL mean inherit from the source specialist.

When a specialist command receives one or more system-skill selectors without an explicit mode, it SHALL store additive mode. When an project-profile command receives one or more system-skill selectors without an explicit mode, it SHALL store additive mode over the inherited source policy.

#### Scenario: Specialist create stores additive utility skill policy
- **WHEN** an operator runs `houmao-mgr project specialist create --name researcher --tool codex --api-key sk-test --system-skill houmao-utils-workspace-mgr`
- **THEN** the persisted specialist records managed system-skill policy as additive
- **AND THEN** the generated compatibility recipe records `houmao-utils-workspace-mgr` under `launch.system_skills`

#### Scenario: Specialist set clears stored system-skill policy
- **WHEN** specialist `researcher` stores additive system-skill policy
- **AND WHEN** an operator runs `houmao-mgr project specialist set --name researcher --clear-system-skills`
- **THEN** the specialist no longer stores explicit managed system-skill policy
- **AND THEN** later launches from the specialist use the packaged managed-launch default selection

#### Scenario: Project profile create stores additive profile policy
- **WHEN** specialist `researcher` already exists
- **AND WHEN** an operator runs `houmao-mgr project profile create --name researcher-workspace --specialist researcher --system-skill houmao-utils-workspace-mgr`
- **THEN** the project profile stores additive managed system-skill policy
- **AND THEN** launches from that profile include the source specialist policy plus `houmao-utils-workspace-mgr`

#### Scenario: Project profile set disables managed system skills
- **WHEN** project profile `researcher-minimal` already exists
- **AND WHEN** an operator runs `houmao-mgr project profile set --name researcher-minimal --no-system-skills`
- **THEN** the project profile stores disabled managed system-skill policy
- **AND THEN** future launches from that profile install no current Houmao-owned system skills

#### Scenario: Invalid easy system-skill name fails clearly
- **WHEN** an operator runs `houmao-mgr project specialist create --name researcher --tool codex --api-key sk-test --system-skill not-a-skill`
- **THEN** the command fails before writing specialist or profile configuration
- **AND THEN** the error identifies the unknown system skill

#### Scenario: Removed easy system-skill name fails clearly
- **WHEN** an operator runs `houmao-mgr project specialist create --name researcher --tool codex --api-key sk-test --system-skill houmao-utils-llm-wiki`
- **THEN** the command fails before writing specialist or profile configuration
- **AND THEN** the error identifies `houmao-utils-llm-wiki` as an unknown system skill
