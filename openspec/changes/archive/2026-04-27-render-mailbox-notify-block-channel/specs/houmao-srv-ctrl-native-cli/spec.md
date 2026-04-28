## MODIFIED Requirements

### Requirement: `houmao-mgr agents mail send` and `post` accept `--notify-block` and respect the houmao-notify body fence
`houmao-mgr agents mail send` and `houmao-mgr agents mail post` SHALL accept an optional `--notify-block <text>` flag whose value populates the canonical envelope's `notify_block.text` field through the supported composition path.

The two commands SHALL also accept an optional `--notify-block-placement [append|prepend]` flag whose value populates `notify_block.placement`. The flag SHALL default to `append`. When `--notify-block` is omitted, `--notify-block-placement` SHALL be ignored and SHALL NOT influence body-fence extraction.

When `--notify-block` is provided, the CLI SHALL submit the canonical envelope's typed `notify_block` shape with the supplied `text` and `placement` through the supported composition contract. The CLI SHALL NOT also re-extract `notify_block` from a `houmao-notify` body fence on top of the explicit value. Composition SHALL apply the canonical auto-mirror invariant (synthesize a `houmao-notify` fenced block in `body_markdown` at the requested `placement` when one is not already present).

When `--notify-block` is omitted and `--body-content` (or the equivalent body-source flag) contains a Markdown fenced code block with info-string `houmao-notify`, the CLI SHALL submit the body source unchanged through the canonical composition contract so the protocol-side extractor populates `notify_block.text` from the first matching fence per the canonical rules and defaults `notify_block.placement` to `"append"`.

The CLI SHALL surface the canonical 512-character truncation outcome and the canonical "verifier not yet supported" rejection as explicit command-line errors, not as Python tracebacks.

The CLI SHALL NOT introduce a separate `--notify-auth-*` family of flags in this change. Callers requiring `notify_auth` metadata SHALL set it through programmatic composition surfaces; the CLI SHALL accept an absent `notify_auth` (treated as no authentication metadata) for normal `send` and `post` invocations.

#### Scenario: Operator supplies an explicit notify-block on send with default placement
- **WHEN** an operator runs `houmao-mgr agents mail send --agent-name alice --to bob@houmao.localhost --subject "..." --body-content "..." --notify-block "re-run on official path"`
- **AND WHEN** the resolved managed-agent authority supports verified mail execution for that send
- **THEN** the canonical mail message stores `notify_block.text="re-run on official path"` and `notify_block.placement="append"`
- **AND THEN** the persisted `body_markdown` contains a `houmao-notify` fenced block matching that text appended after the supplied body content

#### Scenario: Operator supplies notify-block with prepend placement on post
- **WHEN** an operator runs `houmao-mgr agents mail post --agent-name alice --subject "..." --body-content "Operator note." --notify-block "OPERATOR DIRECTIVE" --notify-block-placement prepend`
- **AND WHEN** the resolved managed-agent authority supports verified operator-origin mail execution for that post
- **THEN** the canonical mail message stores `notify_block.text="OPERATOR DIRECTIVE"` and `notify_block.placement="prepend"`
- **AND THEN** the persisted `body_markdown` begins with a `houmao-notify` fenced block matching that text, followed by the supplied body content

#### Scenario: Operator authors notify content via body fence on post
- **WHEN** an operator runs `houmao-mgr agents mail post --agent-name alice --subject "..." --body-content $'hello\n\n` ` ` `houmao-notify\ncontinue current task\n` ` ` `'`
- **AND WHEN** the operator does not pass `--notify-block`
- **AND WHEN** the resolved managed-agent authority supports verified operator-origin mail execution for that post
- **THEN** the canonical mail message stores `notify_block.text="continue current task"` and `notify_block.placement="append"`
- **AND THEN** the persisted `body_markdown` still contains the original fenced block

#### Scenario: Oversize notify-block surfaces a clean CLI error rather than a traceback
- **WHEN** an operator runs `houmao-mgr agents mail send` with `--notify-block` content longer than 512 characters
- **THEN** the canonical composition truncates per the protocol rule and the CLI reports the truncation outcome through explicit command-line output
- **AND THEN** the CLI does not leak a Python traceback from the top-level wrapper

#### Scenario: Unsupported notify-auth scheme surfaces a clean CLI error
- **WHEN** a programmatic composition path attached to an `agents mail` invocation supplies a `notify_auth.scheme` other than `none`
- **THEN** the CLI surfaces the canonical "verifier not yet supported" rejection as an explicit command-line error
- **AND THEN** the CLI does not leak a Python traceback from the top-level wrapper
