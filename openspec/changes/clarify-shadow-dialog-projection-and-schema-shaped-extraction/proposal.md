## Why

Shadow dialog projection is currently useful for lifecycle monitoring, operator inspection, and best-effort cleanup of provider TUI output, but several module names, docs, and call sites still make it easy to read `dialog_projection.dialog_text` as if it were exact extracted reply text. In practice, TUI cleanup is inherently heuristic, provider-version-specific, and vulnerable to redraw drift, and the current projection logic is also too rigid because each provider keeps its projection rules embedded inside one monolithic parser class. Important downstream behavior should depend on schema-shaped outputs and caller-owned extraction patterns rather than on projection fidelity, and the parser stack itself should be refactored so projection logic can be swapped as modular processors.

## What Changes

- **BREAKING** Clarify the contract for `shadow_only` dialog projection as best-effort heuristic cleanup of visible TUI text, not exact transcript recovery and not a reliable answer-extraction surface.
- Refactor provider shadow parsers so dialog projection is produced by modular, swappable projection processors selected by provider/version-aware logic instead of by hardwired monolithic parser methods.
- Tighten runtime and parser guidance so projection remains valid for lifecycle diffing, operator inspection, and caller-owned best-effort pattern matching, while explicitly rejecting any guarantee that the cleaned text matches the provider's exact visible text.
- Require important downstream machine-reading flows to rely on schema-enforcing prompting and explicit extraction rules over available text surfaces instead of assuming the runtime projection is exact.
- Audit and revise affected runtime modules, docs, and demo wording so operator-facing surfaces describe projection as best-effort projected dialog, and runtime-owned structured protocols such as mailbox result handling are framed as schema-driven contracts rather than as generic projection consumers.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `shadow-dialog-projection`: revise the projection contract to define best-effort heuristic cleanup, preserve lifecycle/diagnostic usefulness, and explicitly deny exact-text guarantees.
- `versioned-shadow-parser-stack`: refactor the stack so provider/version-specific projection logic is modular and swappable rather than embedded in one rigid parser implementation.
- `brain-launch-runtime`: revise the shared `shadow_only` result contract and downstream-consumer guidance so reliable machine use depends on schema-shaped output contracts or caller-owned extraction instead of projection fidelity.
- `cao-interactive-demo-inspect-surface`: revise the `--with-output-text` contract so the reported tail is a best-effort projected diagnostic surface rather than a dependable clean-text extraction result.

## Impact

- Affected code: `src/houmao/agents/realm_controller/backends/shadow_parser_core.py`, `src/houmao/agents/realm_controller/backends/shadow_parser_stack.py`, `src/houmao/agents/realm_controller/backends/claude_code_shadow.py`, `src/houmao/agents/realm_controller/backends/codex_shadow.py`, `src/houmao/agents/realm_controller/backends/cao_rest.py`, `src/houmao/agents/realm_controller/backends/shadow_answer_association.py`, `src/houmao/agents/realm_controller/mail_commands.py`, and `src/houmao/demo/cao_interactive_demo/`.
- Affected docs/specs: shadow parser developer docs, realm-controller/runtime reference docs, interactive demo inspect docs, and any mailbox/runtime guidance that currently implies projection is a reliable extracted answer surface.
- Affected callers: `shadow_only` consumers that currently treat `dialog_projection.dialog_text` or demo `output_text_tail` as exact extracted reply text will need to migrate to schema-shaped prompting plus explicit caller-owned extraction rules, and parser-maintenance paths will move from parser-method edits to swappable projector implementations.
