## ADDED Requirements

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
