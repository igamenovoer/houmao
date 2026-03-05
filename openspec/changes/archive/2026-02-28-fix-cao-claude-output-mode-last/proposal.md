## Why

CAO's Claude Code provider currently fails to extract the last assistant message from tmux scrollback when callers request `GET /terminals/{id}/output?mode=last`, returning HTTP `404` ("no ⏺ pattern detected"). In practice this forces downstream callers (including this repo's brain launch runtime) to fall back to `mode=full`, which is raw ANSI/TUI output and can capture spinners/prompts instead of the final answer.

This breaks the expectation that `mode=last` returns a plain, unstyled assistant response for Claude Code.

## What Changes

- Do not modify upstream CAO source code; instead, implement a runtime-side “shadow provider” for Claude Code that fetches `mode=full` output and performs status detection + last-message extraction locally.
- Add runtime-owned parsing presets (markers/spinner/prompt) resolved by version, with an operational env override (`AGENTSYS_CAO_CLAUDE_CODE_VERSION`) for pinning behavior when auto-detection breaks.
- Update the CAO REST backend to use shadow status for readiness/completion (avoid relying on CAO `status` semantics for Claude Code).
- Ensure the runtime never returns raw `mode=full` tmux scrollback as the user-facing response text; return extracted plain text or a clear extraction failure.
- Remove/avoid unsupported output fallbacks (for example `mode=tail`) and reduce wasted HTTP round-trips.

## Capabilities

### New Capabilities

- `cao-claude-code-output-extraction`: Defines the contract for Claude Code response marker detection, shadow status classification, and message extraction from CAO `mode=full` output (including ANSI stripping and prompt boundary detection).

### Modified Capabilities

- (none)

## Impact

- Brain launch runtime behavior (Claude Code output + status handling):
  - `src/agent_system_dissect/agents/brain_launch_runtime/backends/cao_rest.py`
- Add runtime-side parser module(s) under `src/agent_system_dissect/` (no CAO edits).
- Add/update unit tests to pin the expected parsing behavior against representative Claude Code v2.1.62 outputs.
