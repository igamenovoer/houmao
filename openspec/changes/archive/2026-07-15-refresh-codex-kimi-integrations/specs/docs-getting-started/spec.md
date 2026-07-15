## ADDED Requirements

### Requirement: Getting-started guidance describes maintained current Kimi behavior
Getting-started pages SHALL describe Kimi 0.23.x as the maintained Kimi Code family. They SHALL remove Kimi 0.11-specific launch and system-prompt statements and SHALL not instruct users to issue a policy-changing confirmation or `/auto on` bootstrap step during unattended operation.

#### Scenario: New reader sees current Kimi baseline
- **WHEN** a reader opens the overview, quickstart, or system-skills overview
- **THEN** the guidance describes the maintained current Kimi contract
- **AND THEN** it contains no Kimi 0.11.0 compatibility claim

