## MODIFIED Requirements

### Requirement: Launch policy reference documents Kimi unattended TUI auto mode
The launch policy reference SHALL document separate maintained Kimi 0.23.x backend contracts for `kimi_headless` and for Kimi Code TUI through the `raw_launch` launch-policy surface.

The reference SHALL explain that Kimi headless prompt mode remains incompatible with passing `--auto`, `--yolo`, or `--plan`, while Kimi TUI unattended launch uses native `--auto` for fresh and resumed startup. It SHALL state that Houmao does not submit `/auto on` as a conversational bootstrap command.

The reference SHALL state that Kimi auto permission mode is the provider-native no-question setting: normal tool approvals are automatic and `AskUserQuestion` is disabled, but explicit provider hard-deny policies and user-configured deny rules may still block work.

#### Scenario: Reader understands Kimi unattended backend split
- **WHEN** a reader opens the launch policy reference
- **THEN** they can distinguish Kimi headless prompt-mode behavior from Kimi TUI native `--auto` behavior
- **AND THEN** they understand that resumed unattended TUI startup keeps native auto mode

#### Scenario: Reader understands Kimi auto mode boundary
- **WHEN** a reader checks what Kimi unattended does
- **THEN** the reference says normal approvals and questions do not prompt the operator
- **AND THEN** it does not claim that Houmao bypasses explicit hard-deny rules

