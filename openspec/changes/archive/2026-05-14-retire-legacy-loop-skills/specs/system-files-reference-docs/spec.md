## ADDED Requirements

### Requirement: System-files docs mark pairwise-v2 run files as legacy
When system-files docs retain references to `<runtime-root>/loop-runs/pairwise-v2/`, they SHALL mark those paths as legacy runtime artifacts from retired loop packages.

Current pro-generated loop runtime state SHALL be described as generated execplan-specific state unless the pro-generated contract intentionally reuses a legacy path.

#### Scenario: Reader sees pairwise-v2 runtime path
- **WHEN** a reader sees a documented `loop-runs/pairwise-v2` path
- **THEN** the docs identify it as legacy or historical runtime state
- **AND THEN** the docs do not imply that pairwise-v2 is a current packaged skill
