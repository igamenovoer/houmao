## Concise Rendering Contract

This note defines what `detail=concise` means for managed headless rendering. It is the default live and replay mode and must stay stable across Claude, Codex, and Gemini.

`concise` is not a provider log dump and not a lossy "first line only" truncation mode. It is the smallest semantic transcript that still tells an operator:

- what answer the agent produced;
- what executable actions it asked for;
- how those actions ended;
- what final usage/accounting the turn consumed.

## Required Concise Sections

Every provider-specific parser should normalize into the same conceptual sections:

1. Answer text
2. Action request
3. Action result
4. Final completion / usage
5. Optional thinking accounting

The renderer may interleave these sections in streaming order, but the content rules should remain consistent.

## What Must Appear

### 1. Answer text

The assistant's user-visible answer text is the primary content of concise mode. If the provider emits text deltas, the renderer should merge them into normal answer text rather than printing delta bookkeeping.

### 2. Action request

Whenever the model asks to execute something externally visible, concise should print one short line describing the request. "Action" includes more than classic tool calls:

- Claude `tool_use`
- Gemini `tool_use`
- Codex `command_execution`
- Codex `mcp_tool_call`
- Codex `web_search`
- Codex `file_change`

The request line should include the action name and a short argument summary. It should not dump the full raw JSON arguments in human-oriented concise output.

### 3. Action result

Whenever an action yields a success payload, failure payload, exit code, or error message, concise should print one short result line. If the provider does not expose an explicit action result, the renderer should not invent one.

### 4. Final completion / usage

At the end of the turn, concise should print a short footer summarizing completion status and any usage/accounting data that the provider actually exposes and Houmao captures, such as:

- input tokens
- output tokens
- total tokens
- cached tokens
- duration
- cost
- tool-call count

### 5. Optional thinking accounting

Thinking or reasoning counts belong in concise only when they are exposed as compact accounting metadata in machine-readable output captured by Houmao.

Examples:

- Gemini `thoughtsTokenCount` qualifies as concise-friendly accounting when available to Houmao.
- Claude thinking text inside a `ThinkingBlock` does not automatically qualify for concise because it is transcript content, not compact accounting.
- Codex `reasoning.text` is a summary string, not a token count; it should remain detail-oriented.

## What Should Not Appear By Default

In `plain + concise` and `fancy + concise`, the renderer should avoid:

- raw provider JSON objects;
- provider-specific event names that have not been normalized;
- raw nested tool argument dictionaries beyond a short summary;
- raw reasoning/thinking text blocks;
- internal delta bookkeeping;
- session/thread identifiers unless needed for a concise completion footer.

Those details belong in canonical `json` output or `detail` mode.

## Reasoning Visibility Policy

Reasoning is provider-asymmetric, so concise needs a conservative rule:

- Preserve reasoning-related provider payloads in canonical events.
- Show compact thinking accounting in concise when it exists.
- Show visible reasoning text in `detail`, not `concise`, unless a future design intentionally changes this rule.

This keeps concise compact and avoids exposing provider-specific reasoning transcript shapes as the default pane output.

## Provider Capability Matrix

### Claude

- Answer text: yes
- Tool request: yes
- Tool result: yes
- Reasoning text: yes
- Thinking-token count: not guaranteed by the inspected top-level schema

### Codex

- Answer text: yes
- Action request/result: yes
- Reasoning text: yes
- Thinking-token count: not found in the inspected JSON event schema

### Gemini

- Answer text: yes
- Tool request/result: yes
- Reasoning text: yes in lower-level core events
- Thinking-token count: yes in lower-level usage metadata, but not in the public CLI `StreamStats` object

## Canonical Event Expectation

The parser layer should keep enough structure that concise and detail are different renderings of the same canonical event stream rather than separate parsing paths. The canonical event model therefore needs to preserve:

- answer text fragments;
- reasoning fragments or summaries when present;
- action request metadata;
- action result metadata;
- completion and usage metadata;
- provider provenance and raw passthrough payloads for debug/detail surfaces.

## Implementation Alignment In This Change

The current implementation follows this contract with these concrete defaults:

- live managed headless rendering defaults to `style=plain` and `detail=concise`;
- replay through `houmao-mgr agents turn events` uses the same canonical renderer core as the live bridge path;
- canonical `json + detail` includes provider provenance (`provider_event_type`), canonical session identity when known, and `raw` payload context;
- `concise` hides reasoning/session/progress noise unless that information is represented as compact completion or usage accounting;
- when a turn predates `canonical-events.jsonl`, turn readers fall back to the legacy raw-stdout compatibility parser rather than failing inspection.
