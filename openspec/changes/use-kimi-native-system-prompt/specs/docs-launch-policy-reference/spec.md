## MODIFIED Requirements

### Requirement: Launch policy reference documents Kimi unattended TUI auto mode
The launch policy reference SHALL document separate maintained Kimi backend contracts for `kimi_headless` and for Kimi Code TUI through the `raw_launch` launch-policy surface. It SHALL state the minimum-only `>=0.34.0` range, explain that earlier releases are unsupported, and state that support has no upper version limit.

The reference SHALL explain that Kimi headless prompt mode excludes `--auto`, `--yolo`, and `--plan`, while Kimi TUI unattended launch uses native `--auto` for fresh and resumed startup. It SHALL state that Houmao does not submit `/auto on` as a conversational command.

The reference SHALL document native `$KIMI_CODE_HOME/SYSTEM.md` projection, `${base_prompt}` preservation, v2-engine enforcement, rejection of every `${identifier}` placeholder in Houmao prompt text, and conflicts that would bypass the native prompt. It SHALL distinguish this role-injection contract from Kimi permission mode and credential readiness.

#### Scenario: Reader understands Kimi unattended backend split
- **WHEN** a reader opens the launch policy reference
- **THEN** they can distinguish Kimi headless prompt-mode behavior from Kimi TUI native `--auto` behavior
- **AND THEN** they understand that both use native managed-home role-prompt projection before startup

#### Scenario: Reader understands Kimi version and prompt boundaries
- **WHEN** a reader checks the maintained Kimi strategy
- **THEN** the reference identifies the minimum-only `>=0.34.0` range and native `SYSTEM.md` contract
- **AND THEN** it presents no earlier-version or auto-skill fallback

#### Scenario: Reader understands Kimi auto mode boundary
- **WHEN** a reader checks what Kimi unattended mode does
- **THEN** the reference says normal approvals and questions do not prompt the operator
- **AND THEN** it does not conflate permission mode with native role-prompt projection or claim that Houmao bypasses explicit hard-deny rules
