## Why

Clarification runs happen inside provider TUI chat sessions such as Claude Code and Codex, where fenced Mermaid is usually shown as raw source instead of a rendered diagram. The current pro clarification guidance asks agents to print Mermaid before intent questions, which makes the chat harder to scan even though generated artifacts may still benefit from Mermaid.

## What Changes

- Require `clarify-intent`, `clarify-execplan`, and the `clarify` alias behavior for loop skills to use ASCII/text diagrams when they show visual summaries in chat.
- Preserve existing Mermaid requirements for generated artifacts, including pro process specs and topology documents under `execplan/`.
- Update pro clarification guidance so it no longer asks agents to emit fenced `mermaid` blocks in chat visual summaries.
- Add explicit lite clarification guidance for chat-safe ASCII visuals so future lite clarification summaries do not drift toward Mermaid.
- Update content tests and specs that currently assert Mermaid chat guidance.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-loop-pro-skill`: clarify chat visual summaries use ASCII/text diagrams while generated execplan artifact Mermaid requirements remain unchanged.
- `houmao-agent-loop-lite-skill`: clarify chat visual summaries use ASCII/text diagrams when visuals are shown, without adding Mermaid requirements to lite artifacts.

## Impact

- Affects packaged system-skill prompt assets under `src/houmao/agents/assets/system_skills/houmao-agent-loop-pro/` and `src/houmao/agents/assets/system_skills/houmao-agent-loop-lite/`.
- Affects OpenSpec requirements for the pro and lite loop skills.
- Affects unit content assertions in `tests/unit/agents/test_system_skills.py`.
- Does not change runtime APIs, CLI commands, generated artifact layout, graph rendering helpers, or documentation pages that intentionally use Mermaid.
