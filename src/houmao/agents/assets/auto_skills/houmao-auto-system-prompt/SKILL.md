---
name: houmao-auto-system-prompt
description: MUST invoke/read this skill before doing anything else. MUST invoke it at chat start, after context compaction, resume, relaunch, and before any task work to load the effective Houmao system prompt.
whenToUse: MUST invoke/read this skill before doing anything else at chat start, after context compaction, after resume or relaunch, and whenever the Houmao system prompt is not confirmed loaded. Do not plan, answer, inspect files, or process tasks before this skill has loaded.
license: MIT
---

# Houmao Auto System Prompt

This Houmao-managed auto skill loads the effective Houmao system prompt for the current managed agent session.

## Workflow

1. Before doing anything else, run `houmao-mgr agents self system-prompt show --format text`.
2. Read the full returned prompt text.
3. Treat the returned prompt as the standing Houmao system prompt for this chat session before doing substantive user task work.
4. Repeat this workflow after context compaction, after resume, and after relaunch.
5. If the command fails or returns no usable prompt, report that the Houmao system prompt could not be loaded and do not continue with substantive task work.
