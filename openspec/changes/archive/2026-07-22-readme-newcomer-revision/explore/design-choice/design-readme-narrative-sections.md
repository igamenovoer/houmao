# Design Choice: README Narrative Sections

- **Date**: 2026-07-22
- **Change**: `readme-newcomer-revision`
- **Mode**: `design-choice` (sequential, 5 questions)

## Context

The `readme-newcomer-revision` change began as a readability rewrite (define-before-use, single golden-path Quick Start, sentence limits). The operator then directed that the README must keep and strengthen the sections that explain the project: name, metaphor, design rationale, and system architecture. Five decisions resolved the shape of that expansion.

## Decisions

### D1 — Narrative sections are expanded, not just preserved

- **Chosen**: The name/metaphor, design rationale ("Why This Design"), and architecture sections receive richer narrative treatment, not a trim-to-fit rewrite.
- **Rejected**: (A) preserve compactly with one clarifying sentence; (C) compress further toward the fastest possible Quick Start.
- **Consequence**: The README is positioned as a standalone teaching document, not only a funnel into docs.

### D2 — Expansion happens in place, before Quick Start

- **Chosen**: The full narrative sits before Quick Start; the `readme-structure` spec's ~20-line pre-Quick-Start prose cap is relaxed to ~60 lines with required subheadings for scannability.
- **Rejected**: (B) split narrative (short up front, deep section after examples) — recreates the trim shape rejected in D1; (C) push Quick Start below Typical Use Cases — buries the first runnable step.
- **Trade-off accepted**: Action-first readers scroll ~2 screens before install commands. Mitigated by subheadings and an explicit line budget.

### D3 — Quick Start is a complete zero-to-first-agent arc

- **Chosen**: Golden-path steps stay unchanged (install, `command -v tmux`, `npx skills add …`, start CLI agent, `$houmao-admin-welcome start-guided-tour`), but each step states its expected outcome, and the first `You:`/`AI:` exchange (create specialist → launch → review) appears inline inside Quick Start.
- **Rejected**: (A) minimal five-step block ending at tour invocation; (C) checklist-only success criteria.
- **Operator directive**: `$houmao-admin-welcome start-guided-tour` is taught as the one skill invocation every newcomer must remember — if they learn only one skill, it is the welcome skill. This framing appears in Quick Start and in the System Skills section.

### D4 — Architecture teaches both the system view and the single-agent anatomy

- **Chosen**: Narrate the existing team diagram (~15 lines) and add a second mermaid diagram zooming into one managed agent: provider CLI process in tmux, gateway sidecar, mailbox identity, memory directory.
- **Rejected**: (A) system view only — leaves "managed agent", "gateway sidecar", "mailbox identity" abstract; (C) full request-lifecycle walkthrough — duplicates gateway/TUI-tracking docs, highest drift risk.
- **Rationale**: The per-agent anatomy is Houmao's differentiator and the source of the hardest newcomer jargon; picturing it defuses three terms at their point of use.

### D5 — Name and metaphor are brand identity, not a teaching device

- **Chosen (operator custom answer)**: The Houmao / Wukong story stands alone as brand narrative. No metaphor-to-concept mapping block, no teaching role, and metaphor words ("strands", "clones") never become synonyms for canonical terms (`specialist`, `managed agent`).
- **Rejected**: (A) origin story + explicit mapping block; (B) expanded origin with one mapping sentence; (C) recurring metaphor motif throughout the README.
- **Consequence**: Domain language is untouched; no `domain-concepts/` artifact needed. The spec delta carries a guardrail requirement instead of a mapping requirement.

## Coverage Summary

| Category | Status |
| --- | --- |
| Decision type & design space | Resolved (D1) |
| Functional scope & behavior | Resolved (D1–D3) |
| Interaction & UX flow (reading order) | Resolved (D2) |
| Architecture narrative depth | Resolved (D4) |
| Terminology & consistency | Resolved (D5 — canonical terms protected) |
| Conventions & standards | Clear (agent-style sentence rules, existing spec structure) |
| Completion signals | Clear (delta spec scenarios; verify tasks 3.1–3.4) |
| Non-functional, integration, edge cases | Not applicable (documentation change) |

## Next Action

Decisions D1–D5 are synced into the change artifacts (`proposal.md`, `design.md`, `tasks.md`, `specs/readme-structure/spec.md`). Implementation proceeds via the apply phase of `readme-newcomer-revision`.
