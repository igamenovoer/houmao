## ADDED Requirements

### Requirement: Launch-profile-backed launch applies skill overlays
When `houmao-mgr agents launch --launch-profile <name>` uses an explicit launch profile that stores skill overlays, the managed launch SHALL apply those skill overlays during brain-home construction without mutating the source recipe.

When `houmao-mgr project easy instance launch --profile <name>` uses an easy profile that stores skill overlays, the delegated managed launch SHALL apply those skill overlays during brain-home construction without mutating the source specialist.

Registered profile skill refs SHALL be merged with the source preset skills by name and SHALL use the existing registered project skill projection contract.

Private profile skill refs SHALL be projected into the launched agent home from their stored source paths using their stored mode. Copy-mode private skills SHALL copy the source directory contents into the agent home's skill destination. Symlink-mode private skills SHALL create a symlink in the agent home's skill destination pointing at the private source directory.

Private profile skill refs SHALL NOT be imported into `.houmao/content/skills/`, projected into `.houmao/agents/skills/`, or reported by `project skills list`.

If a private profile skill's installed name matches a source preset skill or registered profile skill name, the private profile skill SHALL take precedence in the built agent home.

If a private profile skill source is unavailable or does not contain `SKILL.md` at launch time, the launch SHALL fail clearly before publishing an active managed-agent record.

#### Scenario: Explicit launch profile contributes registered and private skills
- **WHEN** explicit launch profile `reviewer-a` stores registered skill `llm-wiki`
- **AND WHEN** it stores private skill `audit` from `/repo/profile-skills/audit` with mode `copy`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile reviewer-a`
- **THEN** the built agent home includes the source recipe skills
- **AND THEN** it includes registered project skill `llm-wiki`
- **AND THEN** it includes private skill `audit` copied from `/repo/profile-skills/audit`
- **AND THEN** project skill `audit` is not added to the project skill registry

#### Scenario: Easy profile contributes private symlink skill
- **WHEN** easy profile `reviewer-a` stores private skill `live-tools` from `/repo/profile-skills/live-tools` with mode `symlink`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-a`
- **THEN** the built agent home includes private skill `live-tools`
- **AND THEN** the installed private skill path is a symlink to `/repo/profile-skills/live-tools`
- **AND THEN** project skill `live-tools` is not added to the project skill registry

#### Scenario: Private skill takes precedence over registered skill
- **WHEN** the source recipe includes registered skill `notes`
- **AND WHEN** launch profile `reviewer-a` stores private skill source `/repo/profile-skills/notes`
- **AND WHEN** an operator launches from profile `reviewer-a`
- **THEN** the built agent home installs `notes` from `/repo/profile-skills/notes`
- **AND THEN** the registered source skill `notes` does not remain at the installed `notes` destination

#### Scenario: Missing private skill source fails launch
- **WHEN** launch profile `reviewer-a` stores private skill source `/repo/profile-skills/missing`
- **AND WHEN** `/repo/profile-skills/missing/SKILL.md` is unavailable at launch time
- **AND WHEN** an operator launches from profile `reviewer-a`
- **THEN** the launch fails clearly before publishing an active managed-agent record
- **AND THEN** the error identifies the missing private skill source

### Requirement: Launch provenance records profile skill overlays
Managed launch construction provenance SHALL record the launch profile's registered skill refs, private skill refs, and private shadowed skill names when the launch used a profile with skill overlays.

The provenance SHALL identify private skill source paths and modes without embedding private skill file contents.

#### Scenario: Provenance records explicit launch-profile skills
- **WHEN** explicit launch profile `reviewer-a` contributes registered skill `llm-wiki`
- **AND WHEN** it contributes private skill `audit` from `/repo/profile-skills/audit` with mode `copy`
- **AND WHEN** an operator launches from profile `reviewer-a`
- **THEN** the built manifest construction provenance records registered skill ref `llm-wiki`
- **AND THEN** it records private skill `audit`, source path `/repo/profile-skills/audit`, and mode `copy`

#### Scenario: Provenance records private shadowed names
- **WHEN** launch profile `reviewer-a` contributes private skill `notes`
- **AND WHEN** source or registered skills also include `notes`
- **AND WHEN** an operator launches from profile `reviewer-a`
- **THEN** the built manifest construction provenance records `notes` as a private-shadowed skill name
