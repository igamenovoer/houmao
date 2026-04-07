## ADDED Requirements

### Requirement: Launch-profiles guide documents the managed prompt header
The launch-profiles guide SHALL document the Houmao-managed prompt header as part of effective launch-prompt composition.

The guide SHALL explain:
- that managed launches prepend a general Houmao-managed header by default,
- that the header identifies the managed agent and points the agent toward `houmao-mgr` plus supported Houmao system interfaces for Houmao-related work,
- that the header is composed after launch-profile prompt overlay resolution and before backend-specific prompt injection,
- that launch-time override can disable or force the header,
- that stored launch-profile policy can explicitly enable, disable, or inherit the header behavior.

The guide SHALL state that the managed header remains general-purpose and does not rely on naming individual packaged guidance entries.

#### Scenario: Reader understands where the managed header fits in launch-prompt composition
- **WHEN** a reader opens the launch-profiles guide to understand launch-prompt behavior
- **THEN** the page explains that prompt overlay resolution happens before managed-header prepend
- **AND THEN** the page explains that backend-specific prompt injection sees one composed effective launch prompt

#### Scenario: Reader can find the managed-header opt-out story
- **WHEN** a reader looks for how to disable the managed prompt header
- **THEN** the guide explains the launch-time override and stored launch-profile policy surfaces
- **AND THEN** it explains that unset policy falls back to the default enabled behavior
