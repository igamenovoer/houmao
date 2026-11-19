# Spec Delta

## ADDED Requirements

### Requirement: DSH Web selection launches its native browser host

DSH's explicit web mode and its ordinary interactive project default SHALL select `dsh_web`. The browser and structured programmatic controls SHALL target the same owned native host and session. Requesting tui SHALL fail before provider startup until a DSH terminal adapter is qualified.

#### Scenario: A project selects DSH Web

- **WHEN** a DSH project launch has no stored or direct override, or explicitly selects web
- **THEN** the manager publishes the verified native Web surface and the supervised backend dsh_web

#### Scenario: An unsupported DSH terminal is requested

- **WHEN** a caller explicitly selects tui for the supported DSH build
- **THEN** the runtime reports the unsupported pair without starting a browser host

## MODIFIED Requirements

### Requirement: Default non-CAO Codex backend is resumable headless CLI turns
A low-level Codex runtime start without a resolved mode, backend override, or CAO request SHALL default to resumable headless CLI turns. Project birth SHALL pass its separately resolved mode, including its tui default.

#### Scenario: Starting Codex without backend override selects headless backend
- **WHEN** a developer uses the low-level runtime start for Codex without specifying a mode or backend override
- **AND WHEN** the session is not CAO-backed
- **THEN** the runtime selects the Codex headless CLI backend as the default execution mode

## REMOVED Requirements

### Requirement: DSH TUI Posture Resolves to a Web Backend

**Reason**: The supported DSH human interface is a browser.

**Migration**: Select `web` to launch that interface. Explicit `tui` requires an actual terminal UI.
