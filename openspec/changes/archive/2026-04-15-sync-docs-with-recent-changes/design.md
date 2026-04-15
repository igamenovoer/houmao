## Context

Houmao 0.7.0rc1/rc2 introduced several runtime and model changes (manifest schema v4, mailbox `answered` state, agent memory simplification, Copilot system-skills target, writer-team example) but the docs and README were only partially updated. The remaining gaps are factual staleness, contract omissions, and discoverability holes.

## Goals / Non-Goals

**Goals:**

- Bring every factual claim in docs and README into agreement with the current codebase.
- Document the mailbox `answered` state in the canonical model and common workflows reference.
- Make the `examples/writer-team/` template discoverable from the docs site and README demos section.
- Acknowledge Copilot as a supported system-skills install target in the opening framing without overstating it as a launch backend.

**Non-Goals:**

- Rewriting or restructuring the docs site layout.
- Adding new reference pages (all fixes go into existing pages).
- Documenting any code behavior beyond what already shipped in 0.7.0rc1/rc2.
- Updating CHANGELOG (already current).

## Decisions

1. **Schema version fix is a one-line mermaid edit.** The overview.md mermaid node text changes from `schema_version=3` to `schema_version=4`. No prose changes needed — the diagram is the only place this appears.

2. **Mailbox `answered` additions go into the existing canonical-model and common-workflows pages.** The canonical model page already enumerates per-message mutable state fields; `answered` slots in alongside `read`, `starred`, `archived`, `deleted`. The common-workflows page gains a brief note about the answered archive lane. No new page needed.

3. **Writer-team cross-reference in loop-authoring.md** with a "See also" or inline callout rather than duplicating the example README content. The docs index gains one bullet in a new "Examples" subsection or alongside the existing Runnable Demos bullets.

4. **README framing for Copilot uses a parenthetical qualifier** — e.g., "CLI-based AI agents (`claude`, `codex`, `gemini`) with system-skill support for `copilot`" — to avoid implying Copilot is a launch backend.

## Risks / Trade-offs

- [Copilot framing nuance] Mentioning Copilot in the opening line could confuse users into thinking it is a full launch target. → Mitigated by the parenthetical "system-skill support" qualifier and the existing system-skills docs that explain the distinction.
- [Answered state scope] The `answered` lifecycle touches both filesystem mailbox internals and the gateway notifier filter. The docs additions stay at the contract level without exposing internal implementation. → Acceptable for a reference doc.
