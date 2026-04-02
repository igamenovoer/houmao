## ADDED Requirements

### Requirement: README includes a Subsystems at a Glance section

The `README.md` SHALL include a brief section titled "Subsystems at a Glance" with one-liner descriptions and links for the major subsystems: gateway, mailbox, and TUI tracking. The section SHALL point to the corresponding docs pages (GitHub Pages URL or relative docs/ paths).

#### Scenario: Reader finds subsystem pointers in README

- **WHEN** a reader wants to learn about a specific subsystem
- **THEN** the "Subsystems at a Glance" section gives them a one-line description and a link to the full documentation page

#### Scenario: All three major subsystems are listed

- **WHEN** inspecting the subsystems section
- **THEN** it lists gateway (per-agent sidecar for session control and mail), mailbox (unified protocol for filesystem and Stalwart JMAP), and TUI tracking (state machine, detectors, and replay engine)
