## ADDED Requirements

### Requirement: System-skills reference documents minimal skill config
The system-skills CLI reference SHALL document `<tool-home>/.houmao/system-skills/<tool>/houmao-skill-config.json` as the sole manager ownership configuration. It SHALL enumerate the exact four top-level fields and exact four fields in each installed-skill record, explain derived pack selection, and distinguish config `houmao_version`, installed frontmatter version, and content digest evidence.

The reference SHALL use config terminology throughout lifecycle commands and output examples. It SHALL NOT describe a current receipt path or receipt schema.

#### Scenario: Reader inspects ownership state
- **WHEN** a reader wants to understand what Houmao installed
- **THEN** the reference identifies the exact skill-config path and minimal field contract
- **AND THEN** it explains how owner sets preserve shared roots across partial pack uninstall

### Requirement: System-skills reference documents the breaking reinstall boundary
The system-skills reference SHALL state that the current release does not read, migrate, delete, or report `receipt.json`. It SHALL direct users to uninstall with the previous release or remove the old system-skill projections and state before reinstalling.

The reference SHALL continue to explain that doctor can diagnose complete configless copy-paste and Skills CLI installations directly.

#### Scenario: Existing user upgrades from receipt state
- **WHEN** a reader has a receipt-based installation
- **THEN** the reference gives the clean removal and reinstall requirement
- **AND THEN** it does not promise automatic migration or overwrite of old projected roots
