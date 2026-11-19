# Spec Delta

## ADDED Requirements

### Requirement: Definition guidance authors an explicit managed run mode

The packaged definition guidance SHALL use the mode resolver for specialist/profile and raw dossier authoring, fast-forward preparation, and project launch. It SHALL preserve explicit profile defaults and omit an unspecified mode. Unattended policy, gateway attachment, and mailbox defaults SHALL remain independent of mode.

#### Scenario: Profile preparation omits a mode

- **WHEN** the operator prepares an unattended Codex or Claude profile or raw launch dossier without specifying a mode
- **THEN** the instructions omit a mode override and describe the TUI project default

#### Scenario: Fast-forward prepares a DSH profile

- **WHEN** the operator asks for a launchable DSH profile with ordinary interactive defaults
- **THEN** the instructions report the native Web default and a usable launch command

#### Scenario: A specific mode is required

- **WHEN** a caller requests a qualified service or a headless-only lane
- **THEN** the workflow authors that explicit mode and explains an unavailable pair through the supported matrix

### Requirement: Definition guidance uses Kimi's supported project modes

Kimi specialist examples SHALL select `kimi` in project commands and config drafts. Profile and launch guidance SHALL preserve its ordinary TUI default and honor explicitly selected qualified modes. Credential references for supported tools SHALL resolve in the installed skill and route through the documented selection flow.

#### Scenario: A caller authors a Kimi specialist

- **WHEN** the packaged guidance shows a Kimi specialist or project draft
- **THEN** the selected tool is Kimi and the later launch takes the saved or requested mode

#### Scenario: An operator requests another Kimi mode

- **WHEN** a Kimi profile selects an implemented service or Web mode
- **THEN** the launch handoff preserves that mode and reports a limitation for an unsupported installed build

#### Scenario: A credential link is shown

- **WHEN** the installed guidance references Kimi or another maintained tool's credentials
- **THEN** the referenced packaged location exists and documents the supported credential flow

## REMOVED Requirements

### Requirement: `houmao-agent-definition` prefers TUI-supported launch posture when unspecified

**Reason**: Project defaults now follow the selected tool and an explicit four-mode contract.

**Migration**: Use the canonical project mode on profile, dossier, easy launch, and fast-forward paths.

### Requirement: `houmao-agent-definition` supports Kimi specialists, profiles, and launch posture

**Reason**: Kimi examples and credential guidance must follow the current provider set and mode model.

**Migration**: Use Kimi's project default or select one of its qualified modes explicitly.
