## MODIFIED Requirements

### Requirement: Repository SHALL provide tracked reusable dummy skill fixtures for narrow skill-invocation tests
The repository SHALL include at least one tracked reusable dummy skill fixture under `tests/fixtures/agents/skills/` for narrow skill-invocation tests and other supported non-demo validation flows.

That dummy skill fixture SHALL remain small, deterministic, and self-contained. It SHALL define a stable probe contract that causes a visible side effect in the launched dummy-project workdir when the agent invokes the skill through its intended trigger wording.

The dummy skill fixture MAY include helper assets adjacent to `SKILL.md` when needed by the probe contract.

#### Scenario: Maintainer can discover a tracked reusable probe skill fixture
- **WHEN** a maintainer inspects `tests/fixtures/agents/skills/`
- **THEN** the repository contains a tracked reusable probe skill fixture suitable for supported narrow skill-invocation checks
- **AND THEN** that skill fixture is not limited to one pack-local generated run directory

#### Scenario: Probe skill produces a deterministic side effect in the dummy-project workdir
- **WHEN** a live agent session includes the tracked probe skill and receives the skill's documented trigger wording
- **THEN** the probe skill produces the documented marker side effect inside the launched dummy-project workdir
- **AND THEN** that side effect is suitable for test or demo verification

## REMOVED Requirements

### Requirement: Repository SHALL provide lightweight skill-invocation demo agent definitions
**Reason**: The current skill-invocation demo pack is moving to `scripts/demo/legacy/` as archived historical material rather than remaining a maintained supported workflow.
**Migration**: Keep the reusable probe skill fixture itself for supported narrow tests. Define redesigned replacement workflows later as new capabilities instead of preserving the archived demo-specific fixture contract.
