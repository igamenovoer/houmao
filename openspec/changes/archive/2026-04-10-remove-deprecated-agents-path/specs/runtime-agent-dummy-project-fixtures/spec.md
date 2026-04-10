## MODIFIED Requirements

### Requirement: Repository SHALL provide lightweight mailbox-demo presets separate from heavyweight engineering roles
The repository SHALL provide a dedicated lightweight role family for mailbox and runtime-contract tests under `tests/fixtures/plain-agent-def/roles/`.

Those lightweight roles SHALL explicitly bias the agent toward the requested mailbox or runtime-contract action over broad project discovery. They SHALL avoid unrelated benchmarking, CUDA, or large-repo exploration guidance unless a specific fixture explicitly needs that behavior.

The repository SHALL also provide dedicated mailbox-demo named presets at `tests/fixtures/plain-agent-def/presets/mailbox-demo-claude-default.yaml` and `tests/fixtures/plain-agent-def/presets/mailbox-demo-codex-default.yaml` so supported flows can select the lightweight mailbox role through the canonical preset model instead of through legacy recipes or blueprints.

#### Scenario: Maintainer can select dedicated mailbox-demo presets
- **WHEN** a maintainer inspects the tracked plain direct-dir fixture lane for the mailbox/runtime-contract flow
- **THEN** dedicated mailbox-demo presets exist under `tests/fixtures/plain-agent-def/presets/`
- **AND THEN** those presets resolve to the lightweight mailbox-demo role family rather than to the GPU-oriented role family

### Requirement: Repository SHALL provide tracked reusable dummy skill fixtures for narrow skill-invocation tests
The repository SHALL include at least one tracked reusable dummy skill fixture under `tests/fixtures/plain-agent-def/skills/` for narrow skill-invocation tests and other supported non-demo validation flows.

That dummy skill fixture SHALL remain small, deterministic, and self-contained. It SHALL define a stable probe contract that causes a visible side effect in the launched dummy-project workdir when the agent invokes the skill through its intended trigger wording.

The dummy skill fixture MAY include helper assets adjacent to `SKILL.md` when needed by the probe contract.

#### Scenario: Maintainer can discover a tracked reusable probe skill fixture
- **WHEN** a maintainer inspects `tests/fixtures/plain-agent-def/skills/`
- **THEN** the repository contains a tracked reusable probe skill fixture suitable for supported narrow skill-invocation checks
- **AND THEN** that skill fixture is not limited to one pack-local generated run directory

#### Scenario: Probe skill produces a deterministic side effect in the dummy-project workdir
- **WHEN** a live agent session includes the tracked probe skill and receives the skill's documented trigger wording
- **THEN** the probe skill produces the documented marker side effect inside the launched dummy-project workdir
- **AND THEN** that side effect is suitable for test or demo verification
