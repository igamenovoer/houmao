## ADDED Requirements

### Requirement: Kimi unattended TUI startup pre-seeds workspace trust

Maintained Kimi 0.34.0-or-later unattended TUI startup SHALL suppress the provider's workspace-trust confirmation modal by pre-seeding the provider-native trust record for the launch working directory into the managed home before provider start. Houmao SHALL NOT answer the modal conversationally or by simulated keystroke as its suppression mechanism.

#### Scenario: Fresh unattended TUI shows no trust confirmation
- **WHEN** Houmao launches a fresh maintained Kimi TUI with unattended prompt mode and a managed home that has no prior trust state for the working directory
- **THEN** the trust-confirmation modal never mounts during startup
- **AND THEN** the first operator-visible surface is the ready TUI, not a confirmation dialog

#### Scenario: Recorded unattended corpus contains no trust intervention
- **WHEN** a maintained unattended Kimi TUI scenario is recorded for qualification
- **THEN** its labeled timeline contains no trust-confirmation intervention for the launch working directory
- **AND THEN** any residual provider confirmation surface is reported as an explicit exception with evidence
