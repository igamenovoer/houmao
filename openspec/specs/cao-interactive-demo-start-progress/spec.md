# cao-interactive-demo-start-progress Specification

## Purpose
TBD - created by archiving change show-cao-interactive-demo-start-progress. Update Purpose after archive.
## Requirements
### Requirement: Interactive demo startup SHALL emit operator-visible progress breadcrumbs
When a developer runs `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh start` or `launch_alice.sh`, the interactive demo SHALL print human-readable startup progress messages before the final success payload is emitted.

These progress messages SHALL describe major startup stages such as preparing the demo environment, ensuring local CAO availability, building the runtime brain, or launching the interactive session.

#### Scenario: Startup prints progress before final success
- **WHEN** a developer starts the interactive demo and startup takes long enough for multiple stages to occur
- **THEN** the command prints at least one progress breadcrumb before the final success payload
- **AND THEN** the user can tell that startup is still advancing rather than hanging silently

### Requirement: Interactive demo startup SHALL emit periodic waiting feedback during session launch readiness
During the long-running phase where the demo is waiting for the CAO-backed Claude session to launch and become ready for input, the interactive demo SHALL emit recurring waiting feedback until the blocking startup subprocess completes or fails.

This waiting feedback SHALL make it clear that the demo is still waiting for Claude startup/readiness and SHALL include elapsed-time context or an equivalent heartbeat cue that indicates continued liveness.

#### Scenario: Long startup shows recurring wait feedback
- **WHEN** the interactive demo reaches the `start-session` phase and that phase takes longer than a brief initial delay
- **THEN** the command prints a waiting message that explains it is still waiting for the interactive Claude session to become ready
- **AND THEN** additional waiting feedback appears while the subprocess remains active

### Requirement: Interactive demo startup progress SHALL preserve the machine-readable success payload contract
Startup progress output SHALL remain separate from the final structured success payload so existing wrapper behavior and manual scripting can continue to rely on the successful `start` result as machine-readable JSON.

#### Scenario: Final success payload remains machine-readable
- **WHEN** the interactive demo startup succeeds
- **THEN** the final success payload on stdout remains valid machine-readable JSON
- **AND THEN** human-readable progress output does not corrupt or prepend text to that stdout payload

