## Context

Managed headless runtimes currently execute provider CLIs directly on the tmux-backed agent pane and mirror raw stdout/stderr into both the pane and durable artifacts. That works for durability and replay, but it couples operator-facing output to provider-owned JSON protocols and forces later readers to infer meaning from thin `kind/message/payload` event projections.

The current implementation has three useful pieces already in place:

- the headless runner persists raw `stdout.jsonl`, `stderr.log`, `exitcode`, and `process.json` artifacts;
- the runtime already parses raw machine-readable output into `SessionEvent` objects;
- `houmao-mgr` already has a stable `plain` / `json` / `fancy` output vocabulary for human and machine consumers.

What is missing is a canonical semantic layer between provider JSON and Houmao-facing rendering. Without that layer, the live pane, server/passive turn-event APIs, and CLI inspection paths either expose unreadable raw JSON or build ad hoc summaries in multiple places.

This change introduces a normalized headless-output pipeline for Claude, Codex, and Gemini while preserving raw provider artifacts as the debug and compatibility source of truth.

## Goals / Non-Goals

**Goals:**

- Preserve raw provider stdout/stderr artifacts exactly as emitted by the upstream CLI.
- Introduce one canonical normalized headless event model that all later consumers can share.
- Render human-readable live headless output on the tmux pane instead of raw provider JSON.
- Support two orthogonal headless output knobs:
- `style = plain | json | fancy`
- `detail = concise | detail`
- Default live headless rendering to `plain + concise`.
- Define `concise` as the stable default answer-and-actions summary: assistant answer text, provider-exposed thinking/accounting when available, tool or action requests, tool or action results when available, and final usage/completion information.
- Expose canonical headless events and summaries through managed-agent and passive-server inspection surfaces.
- Keep older turn artifacts readable through compatibility fallback.

**Non-Goals:**

- Replacing upstream provider JSON protocols with a Houmao-owned protocol.
- Removing raw `stdout.jsonl` / `stderr.log` artifact access.
- Building a full-screen interactive TUI for headless output.
- Normalizing historical turn artifacts in place.
- Broadly redesigning root-level `houmao-mgr --print-*` behavior outside the headless domain.

## Decisions

### 1. Introduce a headless output bridge process between tmux and the provider CLI

Managed headless turns will no longer stream provider stdout directly to the pane. Instead, the tmux pane will run a Houmao-owned bridge process that:

- launches the provider CLI as a subprocess,
- reads provider stdout/stderr incrementally,
- persists raw provider artifacts,
- parses provider JSON into canonical semantic events,
- renders those semantic events to the pane.

Why this over direct `tee` of provider output:

- it keeps live output readable without sacrificing raw durability;
- it centralizes parsing and rendering instead of duplicating it in CLI, server, and passive-server readers;
- it keeps interrupt/terminate behavior anchored to the same runner-owned process metadata.

Alternative considered:

- keep direct provider execution and post-process artifacts only after completion.
- Rejected because the main user problem is unreadable live output on the tmux pane, not only unreadable post-turn inspection.

### 2. Preserve raw provider artifacts and add a second canonical event artifact

The raw provider outputs remain durable artifacts:

- `stdout.jsonl`: raw provider stdout
- `stderr.log`: raw provider stderr
- existing exit/process markers remain unchanged

The bridge adds a new canonical artifact for normalized headless events, stored separately from raw provider output.

Why this over rewriting `stdout.jsonl` into Houmao-rendered output:

- raw provider output is the safest debugging and compatibility artifact;
- rewriting raw stdout would destroy the exact upstream protocol evidence needed for troubleshooting parser regressions;
- dual artifacts allow gradual migration of downstream readers.

Alternative considered:

- store only canonical events and drop raw stdout after parsing.
- Rejected because parser bugs or upstream provider changes would become much harder to diagnose.

### 3. Separate provider protocol format from operator-facing rendering knobs

The current `output_format = json | stream-json` is a provider-protocol concern and will remain internal to headless launch behavior.

This change adds separate operator-facing rendering controls:

- `display_style = plain | json | fancy`
- `display_detail = concise | detail`

Why this separation:

- provider output-format and operator rendering solve different problems;
- overloading `output_format` would make launch behavior ambiguous and fragile;
- it allows `json` rendering to mean canonical Houmao semantic events rather than raw provider JSON.

Alternative considered:

- reuse `output_format` for both provider protocol and pane rendering.
- Rejected because the same value would mean incompatible things at different layers.

### 4. Normalize provider payloads into semantic event categories

The parser layer will become provider-aware and map raw provider JSON into a shared semantic event model, including categories such as:

- session/chat initialization
- assistant text delta/final
- tool start / tool output / tool finish
- usage / accounting
- completion / failure / diagnostics
- unknown provider event passthrough

Each normalized event will retain provenance such as provider name, provider event type, session/thread identity when available, and optional raw payload when detail mode or debug consumers need it.

Why this over keeping the current generic `kind/message/payload` projection:

- the current shape is too thin for consistent rendering;
- semantic categories make `plain` and `fancy` rendering stable across providers;
- server and passive-server APIs can expose a Houmao contract instead of provider-specific event names.

Alternative considered:

- curate provider-specific renderers without canonical event normalization.
- Rejected because that would duplicate logic and keep inspection APIs provider-shaped.

### 5. Share one headless-domain renderer core between gateway live output and `houmao-mgr` replay, but keep root CLI print-style plumbing separate

The values and general meaning of `plain`, `json`, and `fancy` should match `houmao-mgr`, but live headless rendering is not the same mechanism as root click output dispatch.

This change will introduce a shared headless-domain renderer core that consumes canonical headless semantic events and writes formatted output to a generic text sink. Both the live bridge path and `houmao-mgr agents turn events` replay path will call that same renderer core.

For live execution, the renderer runs inside the Houmao-owned bridge process that replaces direct provider execution on the tmux pane. `houmao-mgr`, the local gateway, and the server-managed gateway remain turn initiators and control-plane callers; they do not need to become the parent process of the provider CLI in order to share rendering behavior.

The root CLI `OutputContext` remains responsible only for resolving the requested style on click-driven command surfaces. It does not become the renderer implementation used by the tmux pane.

Concretely, the intended layering is:

- tmux pane shell → Houmao bridge subprocess → provider CLI
- provider stdout → parser → canonical event → shared headless renderer core → tmux pane
- canonical event artifact → shared headless renderer core → `houmao-mgr` stdout

The shared renderer core should support incremental append-only rendering so it can be used for both live streaming and replay. `json` rendering should be defined by the same headless-domain renderer contract as `plain` and `fancy`, even if the CLI keeps a thin adapter around top-level output framing.

Why this over wiring the pane directly through the existing click output engine:

- the live tmux pane is not a click command response;
- the pane needs incremental streaming renderers rather than whole-payload final renderers;
- `houmao-mgr` replay and gateway live output should share the same semantic rendering code, not just the same style names;
- the shared code boundary is the bridge/CLI renderer library, not process parentage of the provider CLI;
- keeping click style resolution separate avoids coupling gateway output to CLI context objects.

### 6. Define `concise` as a semantic answer-and-actions summary rather than a reduced raw event dump

`concise` is the default operator rendering mode. It should not mean "print fewer provider JSON objects." It should mean "render the smallest stable semantic summary that still explains what the agent did."

For one turn, `concise` should include:

- the assistant answer text as the primary body of the output;
- one tool or action request line whenever the provider emits a tool invocation, command execution, web search, file change, or equivalent executable action;
- one tool or action result line whenever the provider emits a completion payload, success marker, failure marker, or error payload for that action;
- one final completion/usage line with status, token usage, duration, and cost when those fields are available;
- one thinking/accounting line only when the provider exposes a public machine-readable thinking or reasoning count that Houmao actually captures.

`concise` should preserve the user-visible answer while hiding provider-specific structural noise. It should not dump raw payload dictionaries, internal delta bookkeeping, or provider-only event names unless the selected style is canonical `json` or the selected detail level is `detail`.

Visible reasoning text requires a stricter policy:

- Claude `ThinkingBlock.thinking`, Codex `reasoning.text`, and Gemini core `Thought` descriptions should be preserved in canonical events for later inspection.
- Those reasoning texts should default to `detail`, not `concise`, because they are provider-specific and substantially noisier than the answer itself.
- Thinking or reasoning token counts, when available as usage/accounting fields, belong in `concise` because they are compact accounting metadata rather than transcript-like content.

Provider-specific implications:

- Claude: concise can render answer text from `text` blocks, tool request/result from `tool_use` and `tool_result` blocks, and completion/cost from the final `result` object; thinking text is available but should remain detail-oriented.
- Codex: concise can render answer text from `agent_message`, action lifecycle from `command_execution`, `mcp_tool_call`, `web_search`, and `file_change`, and usage from `turn.completed`; the inspected schema does not expose a dedicated thinking-token field.
- Gemini: concise can render answer text, tool request/result, and usage from the public CLI `stream-json` protocol; thinking-token counts are available in lower-level Gemini usage metadata but are not present in the public `StreamStats` object emitted by the current stream formatter.

The provider parsing notes and keyword meanings that motivate this contract are captured in:

- `schema/concise-rendering.md`
- `schema/claude-code-stream-json.md`
- `schema/codex-experimental-json.md`
- `schema/gemini-cli-stream-json.md`

### 7. Downstream readers will prefer canonical events and fall back to legacy raw stdout parsing

Managed-agent local helpers, `houmao-server`, and `houmao-passive-server` will read canonical normalized events when the new artifact exists. For older turns, they will fall back to parsing raw `stdout.jsonl` using the existing compatibility path.

Why this over an all-at-once migration:

- it keeps existing historical turns inspectable;
- it reduces rollout risk because runtime writes the new artifact before all readers fully depend on it.

## Risks / Trade-offs

- [Parser drift across providers] → Keep raw provider artifacts unchanged, record provider event type on canonical events, and add fixture-driven parser tests for Claude, Codex, and Gemini.
- [Streaming renderer complexity] → Keep renderers append-only and line-oriented; avoid a full-screen or cursor-rewriting UI.
- [Contract sprawl across local/server/passive readers] → Introduce one shared artifact reader and one shared canonical event model rather than parallel per-layer parsers.
- [Backward-compatibility confusion between raw and canonical JSON] → Reserve raw JSON for artifact routes and debug surfaces; define `json` display style as canonical Houmao semantic JSON.
- [Over-scoping operator configuration surfaces] → Standardize the knob names and defaults in the runtime first, then wire the selected supported CLI/server launch surfaces to those knobs without inventing provider-specific variants.

## Migration Plan

1. Add the bridge process, canonical normalized event model, and new canonical event artifact while preserving current raw artifacts.
2. Update managed local readers, `houmao-server`, and passive-server compatibility layers to prefer canonical events and fall back to raw stdout parsing for legacy turns.
3. Update live tmux execution to route pane output through the bridge renderer.
4. Expose the new style/detail controls on the supported headless launch and inspection surfaces included in this change.
5. Keep rollback simple by preserving raw provider artifacts and existing exit/process markers; disabling the bridge can revert live output to current raw behavior without losing prior turn data.

## Open Questions

- Which launch surfaces should expose the first user-facing configuration for `display_style` and `display_detail`: only native managed-agent launch paths, or also project-easy specialist/instance creation in the same change?
- How much raw provider payload should remain visible in canonical `json + detail` output before the output becomes as noisy as the current raw stream?
