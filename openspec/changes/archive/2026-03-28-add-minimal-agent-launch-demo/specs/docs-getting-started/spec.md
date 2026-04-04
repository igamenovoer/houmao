## ADDED Requirements

### Requirement: Getting-started docs point to the supported minimal demo

The getting-started documentation SHALL point readers to `scripts/demo/minimal-agent-launch/` as the supported runnable companion to the canonical agent-definition and managed-agent launch documentation.

#### Scenario: Agent-definition docs link to the runnable demo
- **WHEN** a reader finishes the getting-started explanation of the canonical `agents/` directory layout
- **THEN** the page points them to `scripts/demo/minimal-agent-launch/` for a small runnable example that uses the same `skills/`, `roles/`, and `tools/` structure

#### Scenario: Quickstart docs link to the runnable demo
- **WHEN** a reader follows the getting-started quickstart for preset-backed build and launch
- **THEN** the page points them to `scripts/demo/minimal-agent-launch/` as the maintained minimal end-to-end example for local launch
