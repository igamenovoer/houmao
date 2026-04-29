## ADDED Requirements

### Requirement: Explicit launch profiles manage registered and private skill overlays
`houmao-mgr project agents launch-profiles add` and `houmao-mgr project agents launch-profiles set` SHALL support storing profile-owned skill overlays without mutating the referenced source recipe.

The explicit launch-profile surface SHALL accept repeatable `--add-registered-skill <name>` options. Each registered skill name SHALL reference an existing project skill registration by name and SHALL NOT create, import, copy, or symlink a new project skill registration.

The explicit launch-profile surface SHALL accept repeatable `--remove-registered-skill <name>` options on `set`. Removing a registered skill SHALL remove only that launch-profile-owned reference and SHALL NOT remove the project skill registration.

The explicit launch-profile surface SHALL accept repeatable `--add-private-skill <path>` options. Each private skill path SHALL identify a directory containing `SKILL.md`, SHALL derive its installed skill name from that directory name, and SHALL be stored with copy mode.

The explicit launch-profile surface SHALL accept repeatable `--add-private-skill-symlink <path>` options. Each private skill path SHALL identify a directory containing `SKILL.md`, SHALL derive its installed skill name from that directory name, and SHALL be stored with symlink mode.

The explicit launch-profile surface SHALL accept repeatable `--remove-private-skill <path>` options on `set`. Removing a private skill SHALL remove only the matching launch-profile-owned private skill reference and SHALL NOT mutate the referenced source directory.

Adding and removing the same registered skill name or the same normalized private skill path in one command SHALL fail clearly before mutating profile state.

Adding the same private installed skill name more than once in a single launch profile SHALL fail clearly before mutating profile state.

#### Scenario: Add stores registered and copy-mode private skills
- **WHEN** project skill `llm-wiki` is registered
- **AND WHEN** `/repo/profile-skills/audit/SKILL.md` exists
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name reviewer-a --recipe reviewer --add-registered-skill llm-wiki --add-private-skill /repo/profile-skills/audit`
- **THEN** explicit launch profile `reviewer-a` stores registered skill ref `llm-wiki`
- **AND THEN** it stores private skill `audit` with source path `/repo/profile-skills/audit` and mode `copy`
- **AND THEN** project skill `audit` is not added to the project skill registry

#### Scenario: Add stores symlink-mode private skill
- **WHEN** `/repo/profile-skills/live-tools/SKILL.md` exists
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name reviewer-a --recipe reviewer --add-private-skill-symlink /repo/profile-skills/live-tools`
- **THEN** explicit launch profile `reviewer-a` stores private skill `live-tools` with mode `symlink`
- **AND THEN** project skill `live-tools` is not added to the project skill registry

#### Scenario: Set patches registered skill refs
- **WHEN** explicit launch profile `reviewer-a` already stores registered skill ref `llm-wiki`
- **AND WHEN** project skill `project-memory` is registered
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name reviewer-a --remove-registered-skill llm-wiki --add-registered-skill project-memory`
- **THEN** explicit launch profile `reviewer-a` no longer stores registered skill ref `llm-wiki`
- **AND THEN** it stores registered skill ref `project-memory`
- **AND THEN** neither project skill registration is removed

#### Scenario: Set patches private skill refs by normalized path
- **WHEN** explicit launch profile `reviewer-a` already stores private skill source `/repo/profile-skills/audit`
- **AND WHEN** `/repo/profile-skills/audit-next/SKILL.md` exists
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name reviewer-a --remove-private-skill /repo/profile-skills/audit --add-private-skill /repo/profile-skills/audit-next`
- **THEN** explicit launch profile `reviewer-a` no longer stores private source `/repo/profile-skills/audit`
- **AND THEN** it stores private skill `audit-next` with source `/repo/profile-skills/audit-next`
- **AND THEN** neither source directory is deleted or imported into the project skill registry

#### Scenario: Unknown registered skill is rejected
- **WHEN** project skill `unknown-skill` is not registered
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name reviewer-a --recipe reviewer --add-registered-skill unknown-skill`
- **THEN** the command fails clearly before mutating profile state
- **AND THEN** it tells the operator that `unknown-skill` is not a registered project skill

#### Scenario: Invalid private skill path is rejected
- **WHEN** `/repo/profile-skills/bad` does not contain `SKILL.md`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name reviewer-a --recipe reviewer --add-private-skill /repo/profile-skills/bad`
- **THEN** the command fails clearly before mutating profile state
- **AND THEN** project skill `bad` is not added to the project skill registry

### Requirement: Explicit launch-profile inspection and projection report skill overlays
`houmao-mgr project agents launch-profiles get --name <profile>` SHALL report stored registered skill refs and private skill refs as part of the profile defaults.

`houmao-mgr project agents launch-profiles list` SHALL include enough structured skill-overlay summary data for operators to see that a profile contributes additional skills.

The projected `.houmao/agents/launch-profiles/<profile>.yaml` file SHALL render registered skill refs separately from private skill refs. Private skill refs SHALL include installed name, source path, and mode.

#### Scenario: Get reports registered and private skill overlays
- **WHEN** explicit launch profile `reviewer-a` stores registered skill `llm-wiki`
- **AND WHEN** it stores private skill `audit` from `/repo/profile-skills/audit` with mode `copy`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles get --name reviewer-a`
- **THEN** the output reports registered skill ref `llm-wiki`
- **AND THEN** it reports private skill `audit`, its source path, and mode `copy`

#### Scenario: Projection renders skill overlays
- **WHEN** explicit launch profile `reviewer-a` stores registered skill `llm-wiki`
- **AND WHEN** it stores private skill `audit` from `/repo/profile-skills/audit` with mode `symlink`
- **THEN** `.houmao/agents/launch-profiles/reviewer-a.yaml` contains a launch-profile skills block with registered `llm-wiki`
- **AND THEN** that file contains private skill `audit` with source path `/repo/profile-skills/audit` and mode `symlink`
