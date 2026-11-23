# Spec Delta

## ADDED Requirements

### Requirement: Launch-policy reference lists inclusive executable minimums

The reference SHALL list the applicable DSH, Kimi Code, Claude Code, and Codex minimums by launch mode or backend, including accepted release channels. It SHALL explain that newer eligible builds pass the version check and that native startup can still report a protocol, capability, or identity failure. Qualification records SHALL identify the builds actually tested.

#### Scenario: An operator checks which build to install

- **WHEN** an operator looks up a tool and mode in the launch-policy reference
- **THEN** they can identify the applicable minimum and the native startup checks that determine readiness

#### Scenario: A native mode guide names a qualified build

- **WHEN** a Kimi Web, Kimi ACP, or Codex app-server guide cites a tested release
- **THEN** its launch instructions state the inclusive minimum and label the specific release as evidence
