## Claude Code Stream JSON Parsing Notes

This note summarizes the Claude Code machine-readable shapes that Houmao needs to parse for managed headless rendering.

## Invocation Shape

The inspected SDK transport launches Claude Code with `--output-format stream-json --verbose`.

That means Houmao should expect one JSON object per streamed record on stdout rather than one final JSON document.

## Top-Level Record Types

### `type = "assistant"`

Typical raw shape:

```json
{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [
      { "type": "text", "text": "Hello" },
      { "type": "tool_use", "id": "tool_123", "name": "Read", "input": { "file_path": "/test.txt" } }
    ],
    "model": "claude-opus-4-1-20250805"
  },
  "parent_tool_use_id": "toolu_..."
}
```

Meaning:

- `type` selects the top-level envelope.
- `message.content` is the ordered block list that actually matters for parsing answer text, thinking, and tool lifecycle.
- `parent_tool_use_id` indicates nested execution under a prior tool call or subagent context.

### `type = "result"`

Typical raw shape:

```json
{
  "type": "result",
  "subtype": "success",
  "duration_ms": 1000,
  "duration_api_ms": 500,
  "is_error": false,
  "num_turns": 2,
  "session_id": "session_123",
  "stop_reason": "end_turn",
  "result": "Done"
}
```

Meaning:

- `subtype` is Claude's completion category such as success or an error subtype.
- `is_error` is the clearest final success/failure flag.
- `session_id` is the canonical resume identity Houmao should retain.
- `stop_reason` mirrors the model stop reason.
- `usage`, `model_usage`, `total_cost_usd`, `permission_denials`, and `errors` may also appear on this final record.

### `type = "system"`

Claude also emits typed system progress records. The important known `subtype` values are:

- `task_started`
- `task_progress`
- `task_notification`

Typical examples:

```json
{ "type": "system", "subtype": "task_started", "task_id": "task-abc", "description": "Reticulating splines", "uuid": "uuid-1", "session_id": "session-1" }
```

```json
{ "type": "system", "subtype": "task_progress", "task_id": "task-abc", "description": "Halfway there", "usage": { "total_tokens": 1234, "tool_uses": 5, "duration_ms": 9876 }, "last_tool_name": "Read", "uuid": "uuid-2", "session_id": "session-1" }
```

```json
{ "type": "system", "subtype": "task_notification", "task_id": "task-abc", "status": "completed", "output_file": "/tmp/out.md", "summary": "All done", "uuid": "uuid-3", "session_id": "session-1" }
```

Meaning:

- `task_id` identifies one background task.
- `status` on `task_notification` is one of `completed`, `failed`, or `stopped`.
- `last_tool_name` is a progress hint.
- `summary` is a provider-generated short summary of task outcome.

### Optional partial stream events

The SDK also defines `StreamEvent { uuid, session_id, event, parent_tool_use_id }` for partial message streaming. The inspected transport only expects these when `include_partial_messages` is enabled.

Houmao should support passthrough handling for these records if observed, but should not require them for correct parsing of the normal assistant/result flow.

## Content Block Keywords

Inside `assistant.message.content`, the key discriminator is `block.type`.

### `type = "text"`

- `text` is assistant answer text.
- Concatenate these blocks in order for the user-visible answer.

### `type = "thinking"`

- `thinking` is provider-visible reasoning text.
- `signature` is Claude's signature for the thinking block.
- Preserve the text in canonical events, but treat it as detail-oriented content rather than default concise output.

### `type = "tool_use"`

- `id` is the tool request identifier.
- `name` is the tool name.
- `input` is the argument object.

This is the clearest tool-request signal for canonical action-start events.

### `type = "tool_result"`

- `tool_use_id` links the result back to a prior `tool_use`.
- `content` is the returned payload.
- `is_error` indicates failure when present.

This is the clearest tool-result signal for canonical action-finish events.

## Houmao Parsing Rules

1. Parse one JSON object at a time from stdout.
2. Classify by top-level `type`.
3. For `assistant`, inspect `message.content[]` in order.
4. Convert `text` blocks into assistant answer events.
5. Convert `tool_use` blocks into canonical action-request events with request id, tool name, and summarized args.
6. Convert `tool_result` blocks into canonical action-result events with request id, output summary, and error flag.
7. Preserve `thinking` blocks as canonical reasoning events for detail mode.
8. Treat `system` task records as progress/diagnostic events, not answer text.
9. Treat `result` as the turn footer and primary source of session id, usage, cost, stop reason, and success/failure.
10. Preserve unknown top-level `type` values and unknown content-block `type` values as passthrough canonical events.

## Concise-Relevant Fields

For `detail=concise`, Claude parsing should prioritize:

- answer text from `message.content[type=text]`
- tool request from `message.content[type=tool_use]`
- tool result from `message.content[type=tool_result]`
- final status and usage from `type=result`

Thinking policy for concise:

- Do not print raw `thinking` text by default.
- If Claude exposes compact thinking-accounting fields in captured `usage` or `model_usage`, those counts may appear in concise usage output.
- If no compact thinking-accounting field is available, concise should omit thinking rather than repurpose the full `thinking` transcript.

## Known Limits

- The inspected Claude schema clearly exposes reasoning text blocks, but it does not define one obvious mandatory top-level `thinking_tokens` field in the same way Gemini exposes `thoughtsTokenCount` in lower-level usage metadata.
- Claude system task records are useful for progress rendering, but they should not replace the final `result` object as the canonical completion footer.
