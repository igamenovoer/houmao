## MODIFIED Requirements

### Requirement: Run-phase reference explains provider-native relaunch continuation
The run-phase reference SHALL document provider-native chat continuation during tmux-backed relaunch.

The session-lifecycle reference SHALL explain that relaunch reuses the managed session home and tmux window `0`, while the optional relaunch chat-session selector controls whether the provider starts fresh or resumes provider-native history.

The backend reference SHALL include the provider-native startup mapping for Codex, Claude Code, Gemini CLI, and Kimi Code for local interactive relaunch paths and for each provider's maintained native headless relaunch path.

The backend reference SHALL document that Kimi Code TUI resumed startup cannot combine `--continue` or `--session <session_id>` with `--yolo`, `--auto`, or `--plan`, and that `--model <alias>` remains valid with resumed startup.

The backend or launch reference SHALL document that managed `--skills-dir` projection remains Kimi headless prompt-mode behavior and is not claimed for Kimi TUI launch.

The backend or launch reference SHALL document that managed Kimi TUI launches suppress the interactive update preflight by setting `KIMI_CODE_NO_AUTO_UPDATE=1`.

The launch-profile guide or linked run-phase documentation SHALL explain that launch-profile relaunch chat-session policy applies only to later relaunch of instances created from that profile and does not resume provider history on first launch.

#### Scenario: Reader understands TUI relaunch continuation
- **WHEN** a reader opens the run-phase session lifecycle or backend reference
- **THEN** the documentation explains that TUI relaunch continuation is implemented by provider-native startup args before the TUI is respawned
- **AND THEN** it distinguishes that behavior from sending `/resume` or another prompt after startup

#### Scenario: Reader understands launch-profile relaunch policy scope
- **WHEN** a reader opens launch-profile or run-phase documentation for relaunch chat-session policy
- **THEN** the documentation states that the policy applies to relaunch of future instances created from the profile
- **AND THEN** it states that first launch remains normal fresh provider startup

#### Scenario: Reader sees provider mapping table
- **WHEN** a reader needs to verify provider behavior for relaunch continuation
- **THEN** the backend reference includes the Codex, Claude Code, Gemini CLI, and Kimi Code native command forms for maintained TUI and headless latest/exact continuation paths

#### Scenario: Reader sees Kimi-specific launch constraints
- **WHEN** a reader opens the Kimi Code local interactive backend reference
- **THEN** the documentation describes Kimi resume conflicts with `--yolo`, `--auto`, and `--plan`
- **AND THEN** it explains that `--model <alias>` is still allowed and that managed update preflight suppression uses `KIMI_CODE_NO_AUTO_UPDATE=1`
