# Spec Delta

## MODIFIED Requirements

### Requirement: System-skills overview documents pack installation defaults and lifecycle
The guide SHALL explain that external-home CLI installation defaults to the admin pack and managed launch, rebuild, and relaunch default to the agent pack.

#### Scenario: Acceptance criteria
- **GIVEN** a reader who needs to select a supported tool and manage a skill installation
- **THEN** the guide describes explicit pack selection, atomic pack installation, and copy and symlink modes
- **AND THEN** it explains the ownership config, status classifications, upgrade, uninstall, legacy conflicts, and effective-home resolution

#### Scenario: Reader compares external and managed defaults
- **WHEN** a reader needs to know which public skills appear in a home
- **THEN** the guide explains the admin external default and agent managed default
- **AND THEN** it states that no default lane installs both actor packs
