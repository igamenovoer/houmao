## ADDED Requirements

### Requirement: Codex degraded diagnostics use Codex-scoped error types
When the `codex_tui` profile recognizes a bounded prompt-adjacent compact/server degraded failure surface, it SHALL expose structured degraded-context diagnostic metadata in addition to `chat_context=degraded`.

That diagnostic metadata SHALL identify Codex as the owning CLI tool and SHALL use Codex-scoped degraded error type labels for Codex-specific classifications.

Codex degraded error type labels SHALL NOT be treated as a shared cross-tool enum. Other CLI tool profiles SHALL NOT reuse Codex labels unless they are explicitly reporting a Codex TUI surface.

The only degraded error type value that MAY be shared across CLI tool profiles is `unknown`.

The `codex_tui` profile SHALL keep deriving these diagnostics only from bounded prompt-adjacent current-turn compact/server error surfaces, not from arbitrary historical scrollback.

#### Scenario: Codex stream-disconnect compact error gets Codex label
- **WHEN** the current Codex TUI prompt-adjacent terminal failure surface reports a remote compact stream-disconnect style failure
- **THEN** the `codex_tui` profile exposes `chat_context=degraded`
- **AND THEN** the degraded diagnostic identifies the owning CLI tool as Codex
- **AND THEN** the degraded error type uses a Codex-scoped label such as `codex_remote_compact_stream_disconnected`

#### Scenario: Codex context-length compact error gets Codex label
- **WHEN** the current Codex TUI prompt-adjacent terminal failure surface reports that compact input exceeds the model context window
- **THEN** the `codex_tui` profile exposes a Codex-owned degraded diagnostic
- **AND THEN** the degraded error type uses a Codex-scoped label such as `codex_remote_compact_context_length_exceeded`

#### Scenario: Codex unsupported parameter compact error gets Codex label
- **WHEN** the current Codex TUI prompt-adjacent terminal failure surface reports an unsupported compact request parameter
- **THEN** the `codex_tui` profile exposes a Codex-owned degraded diagnostic
- **AND THEN** the degraded error type uses a Codex-scoped label such as `codex_remote_compact_unknown_parameter`

#### Scenario: Unclassified Codex compact error uses unknown
- **WHEN** the current Codex TUI prompt-adjacent terminal failure surface matches compact/server degraded semantics but no Codex-specific error type classification applies
- **THEN** the `codex_tui` profile exposes recoverable degraded chat-context evidence
- **AND THEN** the degraded error type is `unknown`

#### Scenario: Historical Codex compact error has no current diagnostic
- **WHEN** a Codex TUI snapshot contains a historical compact/server error above the current prompt-adjacent region
- **AND WHEN** the bounded current prompt-adjacent region has no compact/server degraded failure surface
- **THEN** the `codex_tui` profile does not expose a current Codex degraded diagnostic from the historical text
- **AND THEN** gateway automation cannot select context recovery from that historical text alone
