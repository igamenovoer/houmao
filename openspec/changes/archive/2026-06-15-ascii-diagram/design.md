## Context

The loop-skill clarification flow runs inside the active agent chat. Pro `clarify-intent` currently instructs agents to show Mermaid diagrams before asking the first clarification question, and the pro spec requires that chat behavior. Provider TUIs such as Claude Code and Codex usually do not render Mermaid in chat, so users see raw Mermaid source instead of a useful visual.

Generated artifacts are a separate surface. Pro execplan generation and validation intentionally require Mermaid diagrams in generated Markdown files such as `execplan/specs/collab/collab-overview.md`, and the repository docs also use Mermaid where Markdown renderers support it. This change should not weaken those artifact contracts.

Lite clarification currently has no explicit visual-summary rule. Because the user asked to check lite and pro, the change should add a small lite guard so any future clarification visuals use the same chat-safe convention.

## Goals / Non-Goals

**Goals:**

- Make clarification chat output use ASCII/text diagrams for architecture, loop structure, topology, route, and coverage summaries.
- Prevent `clarify-intent`, `clarify-execplan`, and the `clarify` alias path from printing fenced `mermaid` blocks in TUI chat.
- Preserve Mermaid requirements for generated execplan artifacts and docs.
- Update OpenSpec requirements and prompt-content tests so the chat-only boundary is enforced.

**Non-Goals:**

- Do not change `houmao-mgr internals graph high render-mermaid`.
- Do not convert existing documentation Mermaid diagrams to ASCII.
- Do not remove generated artifact Mermaid requirements from pro process specs, topology docs, or validation guidance.
- Do not change runtime CLI behavior, generated artifact layout, or graph data models.

## Decisions

1. Treat chat output and generated artifact output as separate rendering surfaces.

   Clarification chat summaries should prefer fenced `text` blocks or plain monospaced ASCII diagrams. Generated Markdown artifacts should continue to follow their existing contracts, including Mermaid where required. Converting all Mermaid to ASCII was rejected because it would weaken artifact documentation and validation contracts that target rendered Markdown pages.

2. Revise pro clarification prompts at the authoring-page level.

   Update pro `subskills/authoring/clarify-intent.md` by replacing its Mermaid-specific visual-summary section with ASCII/text guidance. Add a chat-output guard to pro `subskills/authoring/clarify-execplan.md` so it summarizes generated process or topology diagrams as ASCII in chat rather than pasting Mermaid from generated artifacts. Router-level alias text does not need to duplicate the diagram rule because `clarify` routes into these pages.

3. Add explicit lite clarification chat-visual guidance.

   Add compact chat-visual rules to lite `clarify-intent.md` and `clarify-execplan.md`. Lite does not need the same rich pro visual-summary mandate, but when a lite clarification answer includes a diagram, it should use ASCII/text and avoid fenced `mermaid` blocks in chat.

4. Keep tests as content-contract checks.

   Update the existing system-skill content test that asserts pro Mermaid clarification wording. Add or adjust assertions so pro and lite clarification pages contain ASCII/text chat guidance, and pro clarification no longer contains Mermaid chat instructions. Tests should not assert that generated artifact Mermaid guidance disappeared.

## Risks / Trade-offs

- [Risk] The term "ASCII" could be interpreted as forbidding Unicode box-drawing characters. -> Mitigation: Implementation guidance should say ASCII/text or plain text and prefer simple `+---+`, `|`, `->` diagrams for widest TUI compatibility.
- [Risk] Agents might over-apply the rule and remove generated artifact Mermaid. -> Mitigation: Specs, design, and prompt text must state that the rule is chat-only and does not apply to generated Markdown artifacts.
- [Risk] Lite guidance could become heavier than the lite skill needs. -> Mitigation: Add a short guard rather than a mandatory two-diagram visual-summary workflow.
