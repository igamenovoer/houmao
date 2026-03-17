## MODIFIED Requirements

### Requirement: Interactive demo inspect SHALL optionally include a clean output-text tail
The interactive demo `inspect` command SHALL accept `--with-output-text <num-tail-chars>` as an optional argument.

`<num-tail-chars>` SHALL be a positive integer specifying how many characters of best-effort projected dialog text to include from the tail of the current live TUI snapshot for the persisted tool selection.

When this option is present, the demo SHALL fetch live CAO terminal output using `output?mode=full`, project that scrollback into best-effort dialog text using the runtime-owned parser stack for the persisted tool, and include the last `<num-tail-chars>` characters of that projected dialog text in the inspect result as `output_text_tail`.

The reported `output_text_tail` SHALL come from best-effort projected dialog text, SHALL remain an operator-facing diagnostic surface, SHALL NOT be described as an exact extracted tool reply, and SHALL NOT fall back to raw ANSI or tmux scrollback.

#### Scenario: Inspect returns the requested best-effort dialog tail for the selected tool
- **WHEN** a developer runs `inspect --with-output-text 500` while the live Claude or Codex terminal is reachable
- **THEN** the output includes `output_text_tail` derived from the current best-effort projected dialog text for that tool
- **AND THEN** the returned string contains at most 500 characters from the end of that projected dialog text
- **AND THEN** the command continues to include the normal session, variant, tmux, and log metadata

#### Scenario: Short projected dialog returns the full best-effort text
- **WHEN** a developer runs `inspect --with-output-text 500` and the current projected dialog text is shorter than 500 characters
- **THEN** `output_text_tail` contains the full projected dialog text
- **AND THEN** the command does not pad, truncate incorrectly, or include raw scrollback chrome

#### Scenario: Inspect does not overclaim projection fidelity
- **WHEN** a developer reads `output_text_tail` from inspect output
- **THEN** that field is understood as a best-effort projected diagnostic tail
- **AND THEN** the inspect contract does not imply that the field is an exact extracted tool reply

#### Scenario: Inspect reports output-tail unavailability without using raw scrollback
- **WHEN** a developer runs `inspect --with-output-text 500` and live output fetch or clean projection cannot be completed
- **THEN** the command still prints the base inspection metadata
- **AND THEN** it includes an explicit note that the best-effort output-text tail is unavailable
- **AND THEN** it does not substitute raw `mode=full` or terminal-log content in place of projected dialog text
