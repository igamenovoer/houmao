## ADDED Requirements

### Requirement: Run-phase reference explains provider-native relaunch continuation
The run-phase reference SHALL document provider-native chat continuation during tmux-backed relaunch.

The session-lifecycle reference SHALL explain that relaunch reuses the managed session home and tmux window `0`, while the optional relaunch chat-session selector controls whether the provider starts fresh or resumes provider-native history.

The backend reference SHALL include the provider-native startup mapping for Codex, Claude Code, and Gemini CLI for both local interactive and native headless relaunch paths.

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
- **THEN** the backend reference includes the Codex, Claude Code, and Gemini CLI native command forms for TUI and headless latest/exact continuation
