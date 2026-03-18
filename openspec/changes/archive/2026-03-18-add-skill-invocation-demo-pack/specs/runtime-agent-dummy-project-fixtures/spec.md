## ADDED Requirements

### Requirement: Repository SHALL provide tracked reusable dummy skill fixtures for narrow skill-invocation tests
The repository SHALL include at least one tracked reusable dummy skill fixture under `tests/fixtures/agents/brains/skills/` for narrow skill-invocation demos and tests.

That dummy skill fixture SHALL remain small, deterministic, and self-contained. It SHALL define a stable probe contract that causes a visible side effect in the launched dummy-project workdir when the agent invokes the skill through its intended trigger wording.

The dummy skill fixture MAY include helper assets adjacent to `SKILL.md` when needed by the probe contract.

#### Scenario: Maintainer can discover a tracked reusable probe skill fixture
- **WHEN** a maintainer inspects `tests/fixtures/agents/brains/skills/`
- **THEN** the repository contains a tracked reusable probe skill fixture suitable for skill-invocation demos and tests
- **AND THEN** that skill fixture is not limited to one pack-local generated run directory

#### Scenario: Probe skill produces a deterministic side effect in the dummy-project workdir
- **WHEN** a live agent session includes the tracked probe skill and receives the skill's documented trigger wording
- **THEN** the probe skill produces the documented marker side effect inside the launched dummy-project workdir
- **AND THEN** that side effect is suitable for test or demo verification

### Requirement: Repository SHALL provide lightweight skill-invocation demo agent definitions
The repository SHALL provide dedicated lightweight recipe, role, and blueprint definitions for the skill-invocation demo flow rather than requiring reuse of mailbox-specific or heavyweight engineering fixtures.

At minimum, the tracked fixtures SHALL include:

- a Claude brain recipe for the skill-invocation demo flow,
- a Codex brain recipe for the skill-invocation demo flow,
- a lightweight role package for the skill-invocation demo flow
- a Claude-facing blueprint that binds the Claude recipe to that role
- a Codex-facing blueprint that binds the Codex recipe to that role

The recipes SHALL own the projected probe skill together with the selected config and credential profiles for this narrow demo lane. The blueprints SHALL remain secret-free bindings between those recipes and the lightweight role package.

Those tracked demo definitions SHALL bias the launched agent toward the narrow probe action rather than toward broad repository exploration.

#### Scenario: Maintainer can select skill-invocation demo definitions for Claude and Codex
- **WHEN** a maintainer inspects the tracked agent fixtures used for the skill-invocation demo flow
- **THEN** the repository contains dedicated Claude and Codex demo definitions for that flow
- **AND THEN** those definitions include dedicated recipes that project the tracked probe skill
- **AND THEN** the corresponding blueprints bind those recipes to the lightweight role package needed by the demo

### Requirement: Fixture guidance SHALL explain when to use reusable probe-skill fixtures
The repository fixture guidance SHALL explain when maintainers should use the tracked reusable probe skill and lightweight skill-invocation demo definitions instead of:

- mailbox-demo fixtures, or
- repo-scale heavyweight engineering fixtures.

That guidance SHALL make clear that the probe-skill fixtures are the default choice when the question under test is whether installed skills can be invoked cleanly from a narrow prompt contract.

That same guidance SHALL preserve the current fixture-model boundary: recipes own tool/skill/config/credential selection, while blueprints bind one recipe to one role.

#### Scenario: Fixture documentation distinguishes probe-skill verification from mailbox or repo-scale flows
- **WHEN** a maintainer reads the tracked fixture guidance
- **THEN** the documentation explains when to choose the reusable probe-skill fixture family for narrow skill-invocation checks
- **AND THEN** it distinguishes that choice from mailbox-demo flows and repo-scale engineering flows
