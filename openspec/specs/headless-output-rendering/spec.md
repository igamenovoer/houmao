## Purpose
TBD - synced from change refine-headless-output-rendering. Update Purpose after archive.
## Requirements
### Requirement: Managed headless output preserves raw provider artifacts and emits canonical semantic events
For supported managed headless tools, the runtime SHALL preserve raw provider stdout and stderr as durable artifacts while also emitting a separate canonical normalized event artifact for the same turn.

The raw stdout artifact SHALL contain the upstream provider output as emitted by the CLI rather than Houmao-rendered text.

The canonical event artifact SHALL contain Houmao semantic events derived from that provider output so later readers do not need to parse provider-specific JSON directly.

Unknown or unsupported provider event shapes SHALL be preserved as canonical passthrough events rather than causing the turn to fail solely because one event could not be classified.

#### Scenario: One turn writes both raw and canonical artifacts
- **WHEN** a managed Claude, Codex, Kimi, or Gemini headless turn produces machine-readable stdout
- **THEN** the runtime writes the raw provider stdout artifact for that turn unchanged
- **AND THEN** it also writes a separate canonical normalized event artifact for that same turn

#### Scenario: Unknown provider event does not fail canonicalization
- **WHEN** a supported headless tool emits a machine-readable event that the current parser does not recognize semantically
- **THEN** the runtime preserves that event in the canonical artifact as a provider passthrough or diagnostic event
- **AND THEN** the turn does not fail solely because that event shape was previously unknown

### Requirement: Managed headless live rendering supports style and detail controls
Managed headless live rendering SHALL support two orthogonal controls:

- `style`: `plain`, `json`, or `fancy`
- `detail`: `concise` or `detail`

The default live rendering SHALL be `plain` and `concise`.

`json` style SHALL render canonical Houmao semantic events rather than raw provider stdout.

`detail` mode SHALL expose additional canonical event detail such as provider provenance, normalized session identity, and other structured diagnostic context defined by the canonical event model.

Live managed headless rendering SHALL be performed by the Houmao-owned bridge process running on the tmux pane rather than by whichever control-plane caller initiated the turn.

#### Scenario: Default live rendering is plain and concise
- **WHEN** an operator launches a managed headless runtime without overriding the headless output controls
- **THEN** the live tmux pane shows human-readable plain-text summaries of the turn
- **AND THEN** it does not stream raw provider JSON to the pane by default

#### Scenario: JSON detail mode renders canonical semantic events
- **WHEN** a managed headless runtime is configured with `style=json` and `detail=detail`
- **THEN** the live output is emitted as canonical Houmao semantic JSON events
- **AND THEN** that JSON includes the extra structured detail defined for detail mode rather than raw provider stdout lines

#### Scenario: Fancy concise mode remains human-oriented
- **WHEN** a managed headless runtime is configured with `style=fancy` and `detail=concise`
- **THEN** the live output uses rich human-oriented formatting for assistant and tool progress
- **AND THEN** it omits raw provider payload noise that is reserved for detail mode or raw artifacts

#### Scenario: Live formatting does not depend on caller process parentage
- **WHEN** a managed headless turn is initiated by `houmao-mgr`, a local gateway, or a server-managed gateway
- **THEN** the live pane formatting is produced by the bridge process running on the tmux pane for that turn
- **AND THEN** the initiating caller does not need to be the direct parent process of the provider CLI to obtain the same live rendering behavior

### Requirement: Concise managed headless rendering shows answer text, action lifecycle, and available accounting
For `detail=concise`, managed headless rendering SHALL present a stable semantic summary rather than a reduced dump of raw provider events.

At minimum, concise rendering SHALL include:

- the assistant's user-visible answer text;
- a summary of each tool or executable action request when such a request is emitted by the provider;
- a summary of each tool or executable action result when such a result is emitted by the provider or derived from the provider's explicit action-completion payload;
- a final completion or usage footer using provider-exposed status and accounting fields captured by Houmao.

Thinking or reasoning accounting SHALL appear in concise output only when the provider exposes compact machine-readable accounting fields that Houmao captures for that turn.

Provider-visible reasoning text, summaries, or thought transcripts MAY be preserved in canonical events, but they SHALL default to `detail` rather than `concise` unless they are represented as compact accounting fields.

#### Scenario: Concise rendering includes answer, action request/result, and final usage
- **WHEN** a managed headless turn emits assistant answer text, one tool or action request, one explicit tool or action result, and a final usage footer
- **THEN** `detail=concise` rendering shows the answer text as the primary body of the output
- **AND THEN** it also shows one concise request line, one concise result line, and one final usage or completion line

#### Scenario: Concise rendering does not expose raw reasoning text by default
- **WHEN** a managed headless provider emits provider-visible reasoning text or thought-summary text but does not expose a compact reasoning-accounting field suitable for concise output
- **THEN** `detail=concise` rendering does not print that reasoning text by default
- **AND THEN** the reasoning text remains available through canonical events and `detail` rendering

#### Scenario: Concise rendering does not invent missing action results
- **WHEN** a managed headless provider emits an action request but does not emit an explicit corresponding action-result payload before the turn ends
- **THEN** `detail=concise` rendering shows the action request and any later completion or diagnostic summary that actually exists
- **AND THEN** it does not fabricate a success payload or tool-result line that was never present in provider output

### Requirement: Managed headless live rendering and replayed inspection use the same canonical rendering semantics
For a given canonical headless event stream and a given `style` / `detail` selection, managed headless live rendering and replayed inspection SHALL follow the same headless rendering semantics.

The system MAY adapt transport-specific framing such as top-level CLI envelope shape or sink wiring, but it SHALL NOT require separate provider-specific formatting logic for live pane rendering versus replayed CLI event rendering.

#### Scenario: Live pane and replayed inspection produce the same plain concise summaries
- **WHEN** one canonical headless event sequence is rendered live on the managed headless pane and later replayed through turn-event inspection with `style=plain` and `detail=concise`
- **THEN** both surfaces present the same assistant, tool, and completion summaries in the same semantic order
- **AND THEN** operators do not need to learn different event wording conventions for live monitoring versus replay

#### Scenario: Live pane and replayed inspection produce the same fancy detail semantics
- **WHEN** one canonical headless event sequence is rendered live and replayed with `style=fancy` and `detail=detail`
- **THEN** both surfaces expose the same categories of structured detail for assistant, tool, diagnostic, and completion events
- **AND THEN** neither surface falls back to raw provider JSON solely because it uses a different caller path

### Requirement: Canonical headless events normalize session identity and common execution semantics across providers
The canonical headless event model SHALL normalize provider-specific machine-readable output into shared Houmao execution semantics across Claude, Codex, Kimi, and Gemini.

At minimum, the canonical model SHALL support normalized session identity, assistant output progression, tool lifecycle progression, completion semantics, and provider provenance.

For Codex, provider-owned thread identity SHALL map into the same canonical session-identity field used for Claude and Gemini session identity.

#### Scenario: Codex thread identity becomes canonical session identity
- **WHEN** a managed Codex headless turn emits a provider thread identifier during startup or resume
- **THEN** the canonical event stream records that identifier as the turn's canonical session identity
- **AND THEN** downstream consumers do not need Codex-specific thread-id parsing logic to recover resume identity

#### Scenario: Assistant and tool lifecycle semantics are normalized across providers
- **WHEN** any supported headless provider emits assistant output and tool lifecycle events during one turn
- **THEN** the canonical event stream represents those updates using shared assistant and tool semantic categories
- **AND THEN** downstream renderers can present them without provider-specific event tables

### Requirement: Canonical headless output supports Kimi stream JSON
For managed Kimi headless turns, the runtime SHALL preserve raw Kimi stdout and stderr artifacts while also emitting canonical Houmao semantic events derived from Kimi `stream-json` output.

The canonical Kimi parser SHALL normalize Kimi assistant content, tool calls, tool results, and session resume metadata without requiring downstream consumers to parse Kimi-specific JSONL directly.

Unknown Kimi event shapes SHALL be preserved as canonical passthrough or diagnostic events rather than causing the turn to fail solely because one event could not be classified.

#### Scenario: Kimi assistant content becomes canonical assistant event
- **WHEN** a managed Kimi headless turn emits `{"role":"assistant","content":"done"}` on stdout
- **THEN** the canonical event artifact contains an `assistant` event with message `done`
- **AND THEN** the raw stdout artifact still contains the original Kimi JSONL line unchanged

#### Scenario: Kimi tool calls and tool results become canonical action events
- **WHEN** a managed Kimi headless turn emits an assistant `tool_calls` payload followed by a `role:"tool"` payload with a matching `tool_call_id`
- **THEN** the canonical event artifact contains an `action_request` event for the tool call
- **AND THEN** it contains an `action_result` event for the tool result
- **AND THEN** function arguments encoded as JSON strings are parsed into structured canonical arguments when possible

#### Scenario: Kimi resume hint becomes canonical session identity
- **WHEN** a managed Kimi headless turn emits a meta payload with `type:"session.resume_hint"` and a `session_id`
- **THEN** the canonical event stream records that value as the turn's canonical session identity
- **AND THEN** downstream consumers can recover the Kimi resume identity without provider-specific parsing

#### Scenario: Kimi provider completion is not invented from missing usage data
- **WHEN** a managed Kimi headless turn exits successfully after emitting assistant content and a resume hint but no provider completion or usage payload
- **THEN** the canonical Kimi parser does not fabricate provider usage fields
- **AND THEN** runtime turn completion remains derived from the existing process-exit completion path

### Requirement: Headless output rendering has no Gemini format
Canonical headless output parsing, rendering, and artifact normalization SHALL NOT register or select a Gemini stream format.

#### Scenario: Gemini renderer selection is unavailable
- **WHEN** a caller asks the headless output layer to parse a Gemini stream
- **THEN** the layer rejects the unsupported provider format
- **AND THEN** it does not emit canonical events from Gemini-specific records

### Requirement: Codex collaboration calls use the canonical action lifecycle
The Codex headless parser SHALL normalize `collab_tool_call` started, updated, and completed records into canonical action request and action result events. Canonical data SHALL preserve available collaboration method, sender thread, receiver thread or agent identifiers, prompt, status, and agent-state details.

#### Scenario: Delegated agent call becomes canonical actions
- **WHEN** Codex emits started and completed `collab_tool_call` items for a delegated agent operation
- **THEN** the canonical stream contains a matching action request and action result
- **AND THEN** downstream renderers do not receive those recognized records as generic passthrough events

### Requirement: Kimi retry metadata becomes canonical progress and diagnostics
The Kimi headless parser SHALL normalize `turn.step.retrying` metadata into canonical progress or diagnostic events while preserving failed attempt, next attempt, maximum attempts, delay, status, and error details that Kimi emits.

#### Scenario: Retrying step remains visible without provider-specific parsing
- **WHEN** Kimi stream JSON emits `turn.step.retrying`
- **THEN** the canonical stream reports retry progress with the available attempt and delay fields
- **AND THEN** the raw Kimi payload remains preserved in the raw artifact
