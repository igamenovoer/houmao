## ADDED Requirements

### Requirement: Official live TUI tracking supports Kimi Code TUI
For tmux-backed Kimi Code TUI sessions, the official live TUI tracking path SHALL treat Kimi as a supported surface when a recognized Kimi TUI process is running in the tracked pane process tree.

The maintained Kimi process-name set SHALL include `kimi-code` and `kimi`.

When captured pane text is available for a recognized Kimi TUI process, the parser-owned sidecar path SHALL produce a supported `HoumaoParsedSurface` rather than reporting `unsupported_tool` solely because the tool is Kimi.

The parser-owned Kimi surface SHALL remain sidecar evidence. Shared tracker reduction SHALL continue using raw captured snapshot text as its input.

#### Scenario: Kimi process is recognized as supported
- **WHEN** a tracked tmux pane process tree contains a running process named `kimi-code`
- **THEN** live TUI tracking treats the Kimi TUI process as up and supported
- **AND THEN** the poll cycle can parse captured pane text instead of recording `unsupported_tool`

#### Scenario: Kimi parser produces supported sidecar state
- **WHEN** a recognized Kimi TUI pane is captured successfully
- **THEN** the official parser path returns a `HoumaoParsedSurface` with supported availability
- **AND THEN** the shared tracker still receives the raw captured snapshot text for authoritative state reduction

### Requirement: Kimi Code parser maps visible surfaces to operator state
The Kimi parser SHALL map visible Kimi TUI surfaces into the existing parser-owned operator state vocabulary.

At minimum, the Kimi parser SHALL distinguish:

- prompt-ready main chat surfaces
- active response or tool-use surfaces
- approval dialogs that require operator choice
- startup or modal surfaces such as session picker, login, update, or unknown blocking prompts

The parser SHALL classify approval dialogs as operator-blocked and SHALL expose dialog text that includes the command or question being approved when that text is visible.

The parser SHALL NOT classify Kimi footer model metadata as active-turn evidence by itself.

#### Scenario: Kimi ready surface maps to ready state
- **WHEN** the captured Kimi pane shows a prompt-ready main chat surface with no current blocker
- **THEN** the parsed surface reports an idle or ready business state and freeform input mode

#### Scenario: Kimi approval dialog maps to operator-blocked state
- **WHEN** the captured Kimi pane shows `Run this command?` and approval or rejection choices
- **THEN** the parsed surface reports an operator-blocked state with modal input context
- **AND THEN** the parsed surface includes the visible approval dialog text

#### Scenario: Kimi footer thinking text is not active by itself
- **WHEN** the captured Kimi pane shows footer text containing `thinking`
- **AND WHEN** no current active response, tool-use, or progress surface is visible
- **THEN** the parser does not report active business state solely from that footer text

