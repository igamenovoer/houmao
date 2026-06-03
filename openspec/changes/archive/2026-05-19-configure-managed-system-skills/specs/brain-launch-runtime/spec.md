## ADDED Requirements

### Requirement: Brain build applies effective managed system-skill policy
When brain construction runs for a managed launch, the build pipeline SHALL resolve source recipe system-skill policy and launch-profile system-skill policy into one effective managed system-skill selection before projecting Houmao-owned system skills into the managed home.

The effective selection SHALL be applied after validating requested system-skill sets and names against the packaged system-skill catalog and before the final manifest is written.

The build pipeline SHALL reject selected project registered skills or profile-private skill projections whose names collide with any current packaged Houmao system-skill name.

The generated build manifest or runtime launch metadata SHALL preserve secret-free provenance that identifies the requested source/profile policy and the resolved system-skill names installed into the managed home.

#### Scenario: Source recipe additive policy installs utility skill
- **WHEN** the selected recipe records additive managed system-skill policy for `houmao-utils-llm-wiki`
- **AND WHEN** Houmao builds a managed Codex home from that recipe
- **THEN** the build installs the packaged managed-launch default system skills plus `houmao-utils-llm-wiki`
- **AND THEN** the manifest records the resolved installed system-skill names

#### Scenario: Launch-profile replacement policy overrides source policy
- **WHEN** the source recipe records additive managed system-skill policy for `houmao-utils-llm-wiki`
- **AND WHEN** the selected launch profile records replacement policy using set `core`
- **THEN** the build installs the system-skill selection resolved from `core`
- **AND THEN** it does not install `houmao-utils-llm-wiki` only because the source recipe requested it

#### Scenario: Disabled profile policy produces no installed system skills
- **WHEN** the selected launch profile records disabled managed system-skill policy
- **AND WHEN** Houmao builds or reuses the target managed home
- **THEN** the build leaves no current Houmao-owned system-skill projection paths in the managed home
- **AND THEN** the manifest records an empty resolved system-skill list

#### Scenario: Project skill collision with system skill is rejected
- **WHEN** the selected recipe includes registered project skill `houmao-utils-llm-wiki`
- **AND WHEN** Houmao starts brain construction for a managed launch
- **THEN** the build fails before projecting skills into the managed home
- **AND THEN** the error explains that project/private skill names cannot collide with current Houmao system-skill names

#### Scenario: Manifest records profile system-skill provenance
- **WHEN** a managed agent is launched from profile `researcher-wiki` that stores additive managed system-skill policy
- **THEN** the resulting manifest or launch metadata includes the profile-owned system-skill policy in secret-free provenance
- **AND THEN** later inspection can determine why the managed home received the additional system skill
