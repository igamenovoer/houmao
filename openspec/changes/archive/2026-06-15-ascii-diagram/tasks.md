## 1. Pro Skill Chat Visuals

- [x] 1.1 Revise `src/houmao/agents/assets/system_skills/houmao-agent-loop-pro/subskills/authoring/clarify-intent.md` so the visual summary uses ASCII/text diagrams in chat and no longer asks for fenced `mermaid` blocks.
- [x] 1.2 Revise `src/houmao/agents/assets/system_skills/houmao-agent-loop-pro/subskills/authoring/clarify-execplan.md` so any process or topology summary shown in chat is rendered as ASCII/text rather than pasted Mermaid from generated artifacts.
- [x] 1.3 Confirm pro generated-artifact guidance that intentionally requires Mermaid in `execplan/` process or topology files remains unchanged.

## 2. Lite Skill Chat Visuals

- [x] 2.1 Add concise chat-visual guidance to `src/houmao/agents/assets/system_skills/houmao-agent-loop-lite/subskills/authoring/clarify-intent.md` requiring ASCII/text diagrams for any visual summary shown in chat.
- [x] 2.2 Add matching chat-visual guidance to `src/houmao/agents/assets/system_skills/houmao-agent-loop-lite/subskills/authoring/clarify-execplan.md` without changing generated lite artifact behavior.

## 3. Tests and Validation

- [x] 3.1 Update `tests/unit/agents/test_system_skills.py` content assertions so pro and lite clarification pages require ASCII/text chat guidance and pro clarification no longer asserts Mermaid chat output.
- [x] 3.2 Run `openspec status --change ascii-diagram` and confirm all proposal artifacts are present.
- [x] 3.3 Run the relevant unit test target through Pixi, preferably `pixi run pytest tests/unit/agents/test_system_skills.py` or the repository-supported `pixi run test` if targeted pytest is unavailable.
