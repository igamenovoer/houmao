## ADDED Requirements

### Requirement: `houmao-mgr agents mail send` and `post` accept `--notify-block` and respect the houmao-notify body fence
`houmao-mgr agents mail send` and `houmao-mgr agents mail post` SHALL accept an optional `--notify-block <text>` flag whose value populates the canonical envelope's `notify_block` field through the supported composition path.

When `--notify-block` is provided, the CLI SHALL use the supplied value directly through the canonical composition contract. The CLI SHALL NOT also re-extract `notify_block` from a `houmao-notify` body fence on top of the explicit value.

When `--notify-block` is omitted and `--body-content` (or the equivalent body-source flag) contains a Markdown fenced code block with info-string `houmao-notify`, the CLI SHALL submit the body source unchanged through the canonical composition contract so the protocol-side extractor populates `notify_block` from the first matching fence per the canonical rules.

The CLI SHALL surface the canonical 512-character truncation outcome and the canonical "verifier not yet supported" rejection as explicit command-line errors, not as Python tracebacks.

The CLI SHALL NOT introduce a separate `--notify-auth-*` family of flags in this change. Callers requiring `notify_auth` metadata SHALL set it through programmatic composition surfaces; the CLI SHALL accept an absent `notify_auth` (treated as no authentication metadata) for normal `send` and `post` invocations.

#### Scenario: Operator supplies an explicit notify-block on send
- **WHEN** an operator runs `houmao-mgr agents mail send --agent-name alice --to bob@houmao.localhost --subject "..." --body-content "..." --notify-block "re-run on official timing path"`
- **AND WHEN** the resolved managed-agent authority supports verified mail execution for that send
- **THEN** the canonical mail message stores `notify_block="re-run on official timing path"`
- **AND THEN** the body fence (if any) is not re-extracted on top of the supplied value

#### Scenario: Operator authors notify content via body fence on post
- **WHEN** an operator runs `houmao-mgr agents mail post --agent-name alice --subject "..." --body-content $'hello\n\n```houmao-notify\ncontinue current task\n```'`
- **AND WHEN** the operator does not pass `--notify-block`
- **AND WHEN** the resolved managed-agent authority supports verified operator-origin mail execution for that post
- **THEN** the canonical mail message stores `notify_block="continue current task"`
- **AND THEN** the persisted `body_markdown` still contains the original fenced block

#### Scenario: Oversize notify-block surfaces a clean CLI error rather than a traceback
- **WHEN** an operator runs `houmao-mgr agents mail send` with `--notify-block` content longer than 512 characters
- **THEN** the canonical composition truncates per the protocol rule and the CLI reports the truncation outcome through explicit command-line output
- **AND THEN** the CLI does not leak a Python traceback from the top-level wrapper

#### Scenario: Unsupported notify-auth scheme surfaces a clean CLI error
- **WHEN** a programmatic composition path attached to an `agents mail` invocation supplies a `notify_auth.scheme` other than `none`
- **THEN** the CLI surfaces the canonical "verifier not yet supported" rejection as an explicit command-line error
- **AND THEN** the CLI does not leak a Python traceback from the top-level wrapper
