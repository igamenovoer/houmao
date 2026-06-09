---
name: houmao-auto-system-prompt
description: Read this skill at chat-session start, after context compaction, after resume or relaunch, and before substantive task work when the Houmao system prompt is not confirmed loaded.
whenToUse: Read this skill at chat-session start, after context compaction, after resume or relaunch, and before substantive task work when the Houmao system prompt is not confirmed loaded.
license: MIT
---

# Houmao Auto System Prompt

This Houmao-managed auto skill loads the effective Houmao system prompt for the current managed agent session.

## Workflow

1. Run `houmao-mgr agents self system-prompt show --format text`.
2. Read the full returned prompt text.
3. Treat the returned prompt as the standing Houmao system prompt for this chat session before doing substantive user task work.
4. Repeat this workflow after context compaction, after resume, and after relaunch.
5. If the command fails or returns no usable prompt, report that the Houmao system prompt could not be loaded and do not continue with substantive task work.

Do not read `houmao-memo.md`, inspect runtime manifests directly, or mutate memory as part of loading the system prompt.
