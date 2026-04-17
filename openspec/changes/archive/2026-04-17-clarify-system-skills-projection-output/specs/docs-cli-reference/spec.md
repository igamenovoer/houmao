## ADDED Requirements

### Requirement: CLI reference explains system-skills home and projection output
The CLI reference SHALL document that `houmao-mgr system-skills` plain output distinguishes effective tool homes from tool-native skill projection locations.

The `system-skills` reference SHALL explain that Gemini's effective home may be the project root while Houmao-owned Gemini skills are projected under `<effective-home>/.gemini/skills/`. It SHALL also state that install/status/uninstall output reports enough projection information to locate installed, discovered, removed, or absent skill paths.

#### Scenario: Reader understands Gemini install output
- **WHEN** a reader opens the `system-skills` CLI reference
- **THEN** the page explains that a Gemini home line such as `/workspace/repo` is the effective home
- **AND THEN** the page explains that the corresponding Houmao-owned skill files live under `/workspace/repo/.gemini/skills/`
- **AND THEN** the page describes the projection location information reported by plain install/status/uninstall output
