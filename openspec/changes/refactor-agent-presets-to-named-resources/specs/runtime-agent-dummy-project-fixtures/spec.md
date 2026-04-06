## MODIFIED Requirements

### Requirement: Repository SHALL provide lightweight mailbox-demo presets separate from heavyweight engineering roles
The repository SHALL provide a dedicated lightweight role family for mailbox and runtime-contract tests under `tests/fixtures/agents/roles/`.

Those lightweight roles SHALL explicitly bias the agent toward the requested mailbox or runtime-contract action over broad project discovery. They SHALL avoid unrelated benchmarking, CUDA, or large-repo exploration guidance unless a specific fixture explicitly needs that behavior.

The repository SHALL also provide dedicated mailbox-demo named presets at `tests/fixtures/agents/presets/mailbox-demo-claude-default.yaml` and `tests/fixtures/agents/presets/mailbox-demo-codex-default.yaml` so supported flows can select the lightweight mailbox role through the canonical preset model instead of through legacy recipes or blueprints.

#### Scenario: Maintainer can select dedicated mailbox-demo presets
- **WHEN** a maintainer inspects the tracked agent fixtures for the mailbox/runtime-contract flow
- **THEN** dedicated mailbox-demo presets exist under `presets/`
- **AND THEN** those presets resolve to the lightweight mailbox-demo role family rather than to the GPU-oriented role family
