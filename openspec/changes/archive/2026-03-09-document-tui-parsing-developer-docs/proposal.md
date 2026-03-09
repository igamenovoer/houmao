## Why

The runtime-owned TUI parsing model is now defined by stable OpenSpec deltas and contract notes, but that knowledge is still scattered across a change proposal, contract scratch documents, and a pair of reference/troubleshooting pages. Before `decouple-shadow-state-from-answer-association` is archived, the repository needs official developer-oriented documentation that explains the design, state transitions, and parser/runtime contracts in a durable location.

## What Changes

- Add a developer documentation set under `docs/developer/tui-parsing/` that turns the current change-only contract material into maintained repository docs.
- Split the material into focused pages for architecture, shared parser contracts, runtime lifecycle/state transitions, provider-specific parsing rules, and maintenance/drift handling.
- Add a landing page that explains how the documents relate to each other and where the source-of-truth code and contract inputs live.
- Require the runtime lifecycle documentation to include a Mermaid UML-style state-transition graph and explicit explanations of lifecycle states and transition events.
- Require the Claude and Codex provider pages to include their own Mermaid parser-state transition graphs plus tool-specific explanations of state meanings and transition events.
- Update docs navigation so `docs/index.md` and the existing shadow-parsing reference material point developers at the new deep-dive documentation set.
- Keep existing operator/reference pages concise by linking to the new developer docs instead of duplicating long-form design explanations.

## Capabilities

### New Capabilities
- `tui-parsing-developer-docs`: Provide an official developer documentation set for runtime-owned TUI parsing, covering architecture, shared contracts, runtime state transitions, provider-specific rules, and maintenance guidance.

### Modified Capabilities
- None.

## Impact

- Affected docs: `docs/index.md`, new pages under `docs/developer/tui-parsing/`, and existing reference pages such as `docs/reference/cao_claude_shadow_parsing.md` and `docs/reference/cao_shadow_parser_troubleshooting.md`.
- Affected source material: `openspec/changes/decouple-shadow-state-from-answer-association/design.md` plus `contracts/claude-state-contracts.md`, `contracts/codex-state-contracts.md`, and `contracts/turn-monitor-contracts.md` become the main inputs for the new docs set.
- Runtime code impact: none intended; this is a documentation and navigation change that makes the existing contracts easier for developers to find, review, and maintain.
