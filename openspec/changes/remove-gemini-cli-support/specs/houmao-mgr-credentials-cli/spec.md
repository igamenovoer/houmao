## ADDED Requirements

### Requirement: Credential CLI exposes no Gemini command family
The supported credential tools SHALL be Claude, Codex, and Kimi. The CLI SHALL NOT register Gemini credential CRUD, login, import, rename, or removal commands.

#### Scenario: Gemini credential command is unavailable
- **WHEN** an operator invokes `houmao-mgr project credentials gemini`
- **THEN** command parsing rejects `gemini` as an unsupported credential tool
- **AND THEN** no Gemini auth profile or projected files are created
