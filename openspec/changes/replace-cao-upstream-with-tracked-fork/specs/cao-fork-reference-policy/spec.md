## ADDED Requirements

### Requirement: Active `gig-agents` CAO guidance references the fork repository
Active `gig-agents` operational guidance, knowledge-base notes, and implementation-facing references SHALL use the CAO fork repository as the canonical source reference.

Active guidance SHALL NOT identify `extern/orphan/cli-agent-orchestrator` as the current CAO source location.

#### Scenario: Active source references point at the fork
- **WHEN** a maintainer updates active `gig-agents` CAO docs, specs, or issue notes
- **THEN** repository/source references identify the CAO fork
- **AND THEN** they do not identify `extern/orphan/cli-agent-orchestrator` as the current CAO source location

### Requirement: Active `gig-agents` install guidance uses a fork-backed source
Active `gig-agents` installation, prerequisite, troubleshooting, and `uvx --from` guidance SHALL use a fork-backed CAO source.

That guidance SHALL NOT direct users to `awslabs/cli-agent-orchestrator` or the ambiguous package-name install `uv tool install cli-agent-orchestrator`.

#### Scenario: Install examples use fork-backed CAO guidance
- **WHEN** a user follows active CAO install or `uvx --from` guidance from `gig-agents`
- **THEN** the referenced CAO source is the fork
- **AND THEN** the guidance does not send the user to upstream or the generic package-name install

### Requirement: Provenance exceptions remain scoped
`gig-agents` SHALL allow archive, provenance, or licensing text to remain explicit about original upstream CAO origin when that text is intentionally documenting history or attribution.

Those explicit upstream references SHALL NOT serve as the current operational source-of-truth for active docs, install guidance, or troubleshooting instructions.

#### Scenario: Active guidance is cleaned up while provenance remains explicit
- **WHEN** the CAO fork-reference migration is complete
- **THEN** active operational guidance in `gig-agents` no longer depends on orphan/upstream CAO source references
- **AND THEN** intentionally preserved provenance or licensing text may remain explicit about origin
