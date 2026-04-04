## Codex Experimental JSON Parsing Notes

This note summarizes the streamed JSONL event model emitted by Codex `exec --experimental-json`.

## Invocation Shape

The inspected TypeScript SDK launches Codex with:

```text
codex exec --experimental-json
```

It then reads stdout line by line, so Houmao should treat Codex headless output as newline-delimited top-level JSON events.

## Top-Level Event Keywords

Top-level `type` is the primary discriminator.

### `type = "thread.started"`

```json
{ "type": "thread.started", "thread_id": "thread_123" }
```

Meaning:

- `thread_id` is Codex's resume identity.
- Houmao should normalize this into the same canonical session-identity field used for Claude and Gemini.

### `type = "turn.started"`

Signals the beginning of one new prompt-processing turn. This is useful for boundaries but does not itself carry answer text.

### `type = "turn.completed"`

```json
{
  "type": "turn.completed",
  "usage": {
    "input_tokens": 100,
    "cached_input_tokens": 20,
    "output_tokens": 50
  }
}
```

Meaning:

- this is the main final usage footer for a successful turn;
- the inspected schema exposes input, cached-input, and output counts;
- no dedicated thinking-token field was found in the inspected event schema.

### `type = "turn.failed"`

```json
{ "type": "turn.failed", "error": { "message": "..." } }
```

Meaning:

- fatal turn-level failure;
- should map to canonical completion/failure semantics.

### `type = "item.started" | "item.updated" | "item.completed"`

These wrap one `item` object. `item.id` identifies one logical item across lifecycle updates.

Houmao should parse both the wrapper event type and `item.type`.

## Item Types And Keyword Meanings

### `item.type = "agent_message"`

```json
{ "id": "i1", "type": "agent_message", "text": "Final answer" }
```

Meaning:

- `text` is the assistant answer.
- When structured output is requested, `text` may itself contain JSON text; this is still answer content from the parser's perspective.

### `item.type = "reasoning"`

```json
{ "id": "i2", "type": "reasoning", "text": "Plan and reasoning summary" }
```

Meaning:

- `text` is a reasoning summary visible in the event stream.
- Preserve it for detail mode, but do not assume it represents a token count.

### `item.type = "command_execution"`

```json
{
  "id": "i3",
  "type": "command_execution",
  "command": "rg foo src",
  "aggregated_output": "...",
  "exit_code": 0,
  "status": "completed"
}
```

Meaning:

- `command` is the action request text.
- `aggregated_output` is the collected stdout/stderr.
- `status` is `in_progress`, `completed`, or `failed`.
- `exit_code` only appears when the command exits.

This should map to canonical executable-action lifecycle events even though it is not branded as a "tool" by Codex.

### `item.type = "mcp_tool_call"`

```json
{
  "id": "i4",
  "type": "mcp_tool_call",
  "server": "GitHub",
  "tool": "fetch_pr",
  "arguments": { "pr_number": 12 },
  "result": { "content": [], "structured_content": {} },
  "status": "completed"
}
```

Meaning:

- `server` and `tool` identify the invoked MCP tool.
- `arguments` is the forwarded argument object.
- `result` appears on success.
- `error` appears on failure.
- `status` is `in_progress`, `completed`, or `failed`.

### `item.type = "file_change"`

- `changes` is the list of affected paths and change kinds (`add`, `delete`, `update`).
- `status` is `completed` or `failed`.

This is action-like and should be normalized into canonical action request/result semantics rather than discarded as a special one-off item.

### `item.type = "web_search"`

- `query` is the search request.
- No richer result payload is described in the inspected item shape, so concise should show the request and whatever later completion context is available.

### `item.type = "todo_list"`

- `items[]` is the agent's plan checklist.
- Useful for detail mode, but typically not required in concise output.

### `item.type = "error"`

- `message` is a non-fatal item-level error.
- Preserve as a canonical diagnostic/error event.

## Houmao Parsing Rules

1. Parse Codex stdout as JSONL.
2. Normalize `thread.started.thread_id` into canonical session identity.
3. Use `turn.started` and `turn.completed` or `turn.failed` as turn boundaries.
4. For `item.started` / `item.updated` / `item.completed`, inspect both wrapper `type` and `item.type`.
5. Normalize `agent_message.text` into assistant answer events.
6. Preserve `reasoning.text` in canonical reasoning events for detail mode.
7. Normalize `command_execution`, `mcp_tool_call`, `web_search`, and `file_change` into canonical action lifecycle events.
8. Use `item.id` to correlate lifecycle updates for the same logical action where needed.
9. Use `turn.completed.usage` as the concise usage footer.
10. Preserve unknown future item types as canonical passthrough events rather than failing the turn.

## Concise-Relevant Fields

For `detail=concise`, Codex parsing should prioritize:

- answer text from `agent_message.text`
- action request/result lines from `command_execution`, `mcp_tool_call`, `web_search`, and `file_change`
- final usage from `turn.completed.usage`

Thinking policy for concise:

- the inspected Codex event schema exposes `reasoning.text`, which is a visible summary string;
- no dedicated thinking-token count was found in the inspected top-level event or item schemas;
- concise should therefore omit a thinking-count line by default unless a future captured schema adds one.

## Known Limits

- Codex action lifecycles are item-based rather than one flat `tool_use` / `tool_result` pair, so the parser must use `item.type`, `item.id`, and wrapper lifecycle events together.
- `agent_message.text` may hold structured-output JSON text; concise should still treat it as the answer body rather than trying to reinterpret it as provider control metadata.

## Current Parser Notes

The implementation in this change normalizes Codex records as follows:

- `thread.started` becomes the canonical session event and seeds the shared session-identity field;
- `item.started` for `command_execution`, `mcp_tool_call`, `web_search`, and `file_change` becomes a canonical action request;
- `item.updated` with `status=in_progress` is suppressed for concise replay, while terminal updates map to canonical action results;
- `item.completed.agent_message` becomes assistant output and `item.completed.reasoning` becomes reasoning detail;
- `todo_list` maps to canonical progress detail and remains hidden in default concise human rendering;
- `turn.completed` and `turn.failed` become canonical completion events.
