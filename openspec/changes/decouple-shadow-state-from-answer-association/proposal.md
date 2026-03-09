## Why

The current shadow parser contract asks one component to do two very different jobs: understand the live TUI state of Claude/Codex sessions and also determine which visible text is the "real answer" for the current prompt. For CAO/tmux-backed TUI snapshots, reliable prompt-to-answer association is not a stable parser guarantee, so continuing to encode it in the core shadow parser creates fragile recovery logic and misleading API promises.

## What Changes

- Refocus the core runtime-owned shadow parser contract on provider state detection and transcript projection instead of final-answer association.
- Define frozen shared model shapes for `SurfaceAssessment` and `DialogProjection`, with provider-specific subclasses for Claude and Codex state/projection details.
- Add a caller-facing projected-dialog surface for `shadow_only` sessions that exposes normalized dialog content and transcript slices such as head/tail views.
- **BREAKING**: stop treating shadow-parser-owned answer extraction/turn association as the authoritative runtime contract for CAO TUI sessions; completed turns in `shadow_only` will surface projected dialog content plus parser/runtime state, remove the shadow-mode `output_text` compatibility alias, and make callers responsible for optional answer association heuristics.
- Separate runtime turn monitoring from caller-level answer association so prompt-specific extraction can be implemented as an optional higher layer instead of being embedded into provider TUI parsers.
- Add explicit contract notes for Claude state detection, Codex state detection, and the runtime `TurnMonitor` lifecycle so parser responsibilities and runtime responsibilities are documented separately.
- Ship a small optional associator helper, `TailRegexExtractAssociator(n, pattern)`, as the concrete caller-side extraction example layered on top of projected dialog.
- Tighten docs/specs so unsupported guarantees are removed explicitly rather than preserved as best-effort folklore.

## Capabilities

### New Capabilities
- `shadow-dialog-projection`: Defines the normalized dialog-projection API for shadow-mode sessions, including projected dialog content and caller-facing transcript slice accessors such as head/tail views.

### Modified Capabilities
- `brain-launch-runtime`: Change the runtime contract for `shadow_only` CAO turns so completion is based on shadow state transitions while result payloads surface projected dialog/state instead of parser-owned final-answer extraction.
- `cao-claude-code-output-extraction`: Narrow the Claude shadow-parser contract to supported output-family detection, state classification, and dialog projection; remove the requirement that the core Claude parser reliably associate/extract the final answer for the current prompt.
- `cao-codex-output-extraction`: Align Codex shadow parsing with the same separation of concerns so the shared shadow-parser API is consistent across TUI providers.
- `versioned-shadow-parser-stack`: Change the shared stack contract from "status plus extracted answer" to "status plus projected dialog and parser metadata," leaving answer association to a separate optional layer.

## Impact

- Affected code: `src/gig_agents/agents/brain_launch_runtime/backends/shadow_parser_core.py`, `shadow_parser_stack.py`, `cao_rest.py`, `claude_code_shadow.py`, `codex_shadow.py`, and runtime result/event payload shaping.
- Affected docs/specs: CAO shadow parsing reference docs, runtime reference docs, and shadow parser troubleshooting guidance.
- Affected callers/tests: CAO `shadow_only` unit/integration tests and any caller that currently assumes `output_text` from shadow parsing is the authoritative final answer for the just-submitted prompt; those callers will need to read `dialog_projection` / `surface_assessment` fields or opt into an associator helper.
