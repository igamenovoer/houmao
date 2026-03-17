## Why

Shadow dialog projection is currently useful for lifecycle monitoring, operator inspection, and best-effort cleanup of provider TUI output, but several module names, docs, and call sites still make it easy to read `dialog_projection.dialog_text` as if it were exact extracted reply text. In practice, TUI cleanup is inherently heuristic, provider-version-specific, and vulnerable to redraw drift, and the current projection logic is also too rigid because each provider keeps its projection rules embedded inside one monolithic parser class. Important downstream behavior should depend on schema-shaped outputs and caller-owned extraction patterns rather than on projection fidelity, and the parser stack itself should be refactored so projection logic can be swapped as modular processors.

The core CAO runtime already resolves `shadow_only` by default for supported CAO-backed Claude and Codex sessions, but several repo-owned docs, demos, report verifiers, and incidental test helpers still model `cao_only` extraction or `done.message` reply text as if that were the ordinary contract. As the repo increasingly relies on the shadow parser, those mixed assumptions make the shadow-first posture fragile and encourage downstream consumers to depend on the wrong text surface.

## What Changes

- **BREAKING** Clarify the contract for `shadow_only` dialog projection as best-effort heuristic cleanup of visible TUI text, not exact transcript recovery and not a reliable answer-extraction surface.
- Refactor provider shadow parsers so dialog projection is produced by modular, swappable projection processors selected by provider/version-aware logic instead of by hardwired monolithic parser methods.
- Expand the change so repo-owned CAO-backed Claude/Codex workflows, docs, demo packs, and incidental test helpers treat `shadow_only` as the default posture and reserve `cao_only` for explicit CAO-native coverage, debugging, or incident-response paths.
- Tighten runtime and parser guidance so projection remains valid for lifecycle diffing, operator inspection, and caller-owned best-effort pattern matching, while explicitly rejecting any guarantee that the cleaned text matches the provider's exact visible text.
- Require important downstream machine-reading flows to rely on schema-enforcing prompting and explicit extraction rules over available text surfaces instead of assuming the runtime projection is exact.
- Audit and revise affected runtime modules, docs, and demo wording so operator-facing surfaces describe projection as best-effort projected dialog, and runtime-owned structured protocols such as mailbox result handling are framed as schema-driven contracts rather than as generic projection consumers.
- Revise demo/report surfaces that currently require non-empty `response_text` or scrape the final `done.message` so default shadow-mode success and verification rely on structured completion, side-effect contracts, explicit schema/sentinel outputs, or clearly labeled best-effort shadow extraction instead of CAO-native answer-text assumptions.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `shadow-dialog-projection`: revise the projection contract to define best-effort heuristic cleanup, preserve lifecycle/diagnostic usefulness, and explicitly deny exact-text guarantees.
- `versioned-shadow-parser-stack`: refactor the stack so provider/version-specific projection logic is modular and swappable rather than embedded in one rigid parser implementation, and route repo-owned shadow-aware helper code through the shared stack-level abstraction.
- `brain-launch-runtime`: revise the shared `shadow_only` result contract and downstream-consumer guidance so reliable machine use depends on schema-shaped output contracts or caller-owned extraction instead of projection fidelity, while repo-owned CAO workflows for supported tools follow the shadow-first posture by default.
- `cao-interactive-demo-inspect-surface`: revise the `--with-output-text` contract so the reported tail is a best-effort projected diagnostic surface rather than a dependable clean-text extraction result.
- `cao-interactive-full-pipeline-demo`: revise turn artifacts and verification so shadow-mode completion does not depend on `done.message` or a mandatory authoritative `response_text` field.
- `cao-claude-demo-scripts`: revise CAO Claude demo-pack success criteria so default shadow-mode runs rely on side effects or explicit shadow-aware extraction rather than CAO-native reply-text assumptions.

## Impact

- Affected code: `src/houmao/agents/realm_controller/backends/shadow_parser_core.py`, `src/houmao/agents/realm_controller/backends/shadow_parser_stack.py`, `src/houmao/agents/realm_controller/backends/claude_code_shadow.py`, `src/houmao/agents/realm_controller/backends/codex_shadow.py`, `src/houmao/agents/realm_controller/backends/cao_rest.py`, `src/houmao/agents/realm_controller/backends/shadow_answer_association.py`, `src/houmao/agents/realm_controller/mail_commands.py`, `src/houmao/demo/cao_interactive_demo/`, `scripts/demo/cao-interactive-full-pipeline-demo/`, `scripts/demo/cao-claude-session/`, `scripts/demo/cao-codex-session/`, `scripts/demo/cao-claude-tmp-write/`, and `scripts/demo/cao-claude-esc-interrupt/`.
- Affected docs/specs: shadow parser developer docs, realm-controller/runtime reference docs, interactive demo inspect docs, interactive full-pipeline demo docs/specs, Claude CAO demo-pack docs/specs, and any mailbox/runtime guidance that currently implies projection or `done.message` is a reliable extracted answer surface.
- Affected callers: `shadow_only` consumers that currently treat `dialog_projection.dialog_text`, demo `output_text_tail`, or CAO runtime `done.message` as exact extracted reply text will need to migrate to schema-shaped prompting plus explicit caller-owned extraction rules or shadow-aware best-effort diagnostics, and parser-maintenance paths will move from parser-method edits to swappable projector implementations.
