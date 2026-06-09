## ADDED Requirements

### Requirement: Launch policy reference documents Kimi unattended TUI auto mode
The launch policy reference SHALL document that maintained Kimi unattended behavior has separate backend contracts for `kimi_headless` and for Kimi Code TUI through the `raw_launch` launch-policy surface.

The reference SHALL explain that Kimi headless prompt mode remains incompatible with passing `--auto`, `--yolo`, or `--plan`, while Kimi TUI unattended launch uses Kimi auto permission mode through managed runtime-home config and runtime startup refresh rather than a persistent `--auto` launch argument.

The reference SHALL state that Kimi auto permission mode is the provider-native no-question setting: normal tool approvals are automatic and `AskUserQuestion` is disabled, but explicit provider hard-deny policies and user-configured deny rules may still block work.

#### Scenario: Reader understands Kimi unattended backend split
- **WHEN** a reader opens the launch policy reference
- **THEN** they can distinguish Kimi headless prompt-mode unattended behavior from Kimi TUI raw-launch unattended behavior
- **AND THEN** they understand why Kimi TUI unattended behavior is not implemented by adding `--auto` to every startup command

#### Scenario: Reader understands Kimi auto mode boundary
- **WHEN** a reader checks what Kimi unattended does
- **THEN** the reference says Kimi auto mode avoids tool approval prompts and user questions during normal work
- **AND THEN** it does not claim that Houmao bypasses explicit Kimi hard-deny rules
