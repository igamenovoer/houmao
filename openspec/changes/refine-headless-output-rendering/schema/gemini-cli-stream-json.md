## Gemini CLI Stream JSON Parsing Notes

This note distinguishes between Gemini's public CLI `stream-json` protocol and its richer lower-level core stream. Houmao's parser design needs to know both because the public protocol is what current CLI output exposes, but the lower-level stream explains where hidden capability gaps come from.

## Public CLI Output Formats

The inspected Gemini CLI supports:

- `--output-format json`
- `--output-format stream-json`

The public streaming parser should target `stream-json`.

## Public `stream-json` Event Types

Top-level `type` is the discriminator.

### `type = "init"`

```json
{ "type": "init", "timestamp": "...", "session_id": "session-1", "model": "gemini-..." }
```

Meaning:

- `session_id` is Gemini's resume identity.
- `model` is the selected model name.

### `type = "message"`

```json
{ "type": "message", "timestamp": "...", "role": "assistant", "content": "4", "delta": true }
```

Meaning:

- `role` is `user` or `assistant`.
- `content` is the message text fragment.
- `delta = true` means this is an incremental text chunk rather than one complete final message.

For concise rendering, Houmao should merge assistant message deltas into normal answer text rather than printing one line per delta chunk.

### `type = "tool_use"`

```json
{ "type": "tool_use", "timestamp": "...", "tool_name": "Read", "tool_id": "read-123", "parameters": { "file_path": "/path/to/file.txt" } }
```

Meaning:

- `tool_name` is the tool name.
- `tool_id` is the request identifier.
- `parameters` is the argument object.

### `type = "tool_result"`

```json
{ "type": "tool_result", "timestamp": "...", "tool_id": "read-123", "status": "success", "output": "File contents here" }
```

or

```json
{ "type": "tool_result", "timestamp": "...", "tool_id": "read-123", "status": "error", "error": { "type": "FILE_NOT_FOUND", "message": "File not found" } }
```

Meaning:

- `tool_id` links back to the prior `tool_use`.
- `status` is `success` or `error`.
- `output` carries success output.
- `error.type` and `error.message` carry failure detail.

### `type = "error"`

- `severity` is `warning` or `error`.
- `message` is the diagnostic text.

### `type = "result"`

```json
{
  "type": "result",
  "timestamp": "...",
  "status": "success",
  "stats": {
    "total_tokens": 100,
    "input_tokens": 50,
    "output_tokens": 50,
    "cached": 0,
    "input": 50,
    "duration_ms": 1200,
    "tool_calls": 2,
    "models": {}
  }
}
```

Meaning:

- `status` is `success` or `error`.
- `error` may appear on failure.
- `stats` is the public concise-friendly usage footer.

## Lower-Level Core Stream Keywords

Gemini's internal core stream is richer than the public `stream-json` schema. The important lower-level event types are:

- `content`
- `thought`
- `tool_call_request`
- `tool_call_response`
- `finished`

Important keyword meanings:

- `GeminiEventType.Thought` carries a `ThoughtSummary`.
- `ToolCallRequest.value.name` and `.args` describe the request.
- `ToolCallResponse.value.resultDisplay`, `.responseParts`, `.error`, and `.data` describe the result.
- `Finished.value.usageMetadata` contains lower-level usage accounting from the model response.

The inspected raw integration fixture shows:

- `parts[].thought = true`
- `parts[].text` with visible thought text
- `functionCall.name`
- `functionCall.args`
- `usageMetadata.thoughtsTokenCount`

## Houmao Parsing Rules

1. Parse the public CLI `stream-json` protocol directly when that is what stdout contains.
2. Use `init.session_id` as canonical session identity.
3. Merge assistant `message` events into answer text, respecting `delta`.
4. Map `tool_use` directly to canonical action-request events.
5. Map `tool_result` directly to canonical action-result events.
6. Use `result` as the public completion/usage footer.
7. Preserve `error` events as diagnostics.
8. If Houmao later captures richer Gemini core events, map `thought`, `tool_call_request`, and `tool_call_response` into the same canonical event categories rather than introducing a separate rendering path.

## Concise-Relevant Fields

For `detail=concise`, Gemini parsing should prioritize:

- answer text from `message` events with `role = assistant`
- tool request from `tool_use`
- tool result from `tool_result`
- usage and completion status from `result.stats`

Thinking policy for concise:

- the lower-level Gemini model usage metadata exposes `thoughtsTokenCount`;
- the public `StreamStats` shape emitted by the inspected `stream-json` formatter does not include a `thoughts` or `thoughts_token_count` field;
- concise can only show Gemini thinking-token counts if Houmao captures richer data than the current public `stream-json` footer.

## Known Limits

- The public CLI `stream-json` protocol is flatter than the internal Gemini core stream. It is sufficient for answer text and tool lifecycle rendering, but it hides some reasoning-specific information that exists internally.
- If Houmao sticks to public `stream-json` only, Gemini concise output should not pretend to know the thinking-token count when that count is absent from the captured public stream.

## Current Parser Notes

The implementation in this change normalizes Gemini records as follows:

- `init` becomes the canonical session event and provides the shared session identity;
- assistant `message` records become canonical assistant output and are merged into the answer body during replay;
- `tool_use` and `tool_result` become canonical action request/result events;
- `error` becomes a canonical diagnostic event;
- `result.stats` becomes the canonical completion and usage footer;
- because the public CLI footer does not expose thinking-token counts, default concise rendering omits Gemini reasoning/accounting lines unless richer captured data becomes available later.
