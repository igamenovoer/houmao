# Quickstart Branch

Use this branch when the user wants to reach one running managed agent with the minimum number of decisions. This branch is appropriate for a blank-slate workspace or for any caller who explicitly asks for a "quickstart" path.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Detect which supported tool CLIs are available on the host by running a presence check for each tool adapter shipped with the packaged Houmao distribution:
   - `command -v claude`
   - `command -v codex`
   - `command -v gemini`
3. List the detected tool CLIs to the user without priority, without ordering that implies recommendation, and without marking any detected tool as the default or preferred tool. When more than one tool is detected, ask the user which one to use before proceeding.
4. When the workspace has no project overlay, route project initialization through `houmao-project-mgr` first. Do not attempt specialist authoring before the overlay exists.
5. Route specialist authoring, credential attachment, and easy-instance launch through `houmao-specialist-mgr`. Let that skill own the concrete command shapes; this branch only carries the minimum-viable decisions:
   - one specialist name the user can remember (see `references/question-style.md` and `references/concepts.md` for vocabulary),
   - one credential for the chosen tool (API key or locally signed-in credential),
   - one managed-agent instance name for the launch.
6. Advise foreground-first gateway posture for tmux-backed first-run launches in the same way as the rest of the tour; carry that rule into the downstream skill rather than restating the launch flags here.
7. After the first launch succeeds, summarize the new current state and offer the next likely branches:
   - send a normal prompt,
   - watch live gateway or TUI state,
   - enable automatic email notification when mailbox accounts are set up,
   - create another specialist or launch another agent,
   - explore advanced usage through the features enumeration branch.

## No Tool Detected

When `command -v claude`, `command -v codex`, and `command -v gemini` all fail:

- Explain that the packaged Houmao distribution currently ships tool adapters for `claude`, `codex`, and `gemini`.
- Name each supported tool CLI so the user can install whichever one they prefer.
- Do not attempt to launch a managed agent in that turn.
- Offer to resume the quickstart branch after the user installs one of the supported tool CLIs.

## Tool Listing Style

- List the detected tools in a flat bullet list.
- Do not annotate any entry as "recommended", "preferred", "primary", or "default".
- Do not sort by tool name, release date, or any other attribute that the user could read as an implicit ranking.
- When only one supported tool is detected, list that one tool on its own line without ceremony and continue; the single detected tool still is not "the default", it is just the only one present.

## Typical Questions

- "Which tool do you want this first agent to use?" (only when more than one tool CLI was detected)
- "What specialist name do you want?" (route to `houmao-specialist-mgr`; see `references/question-style.md`)
- "Which credential do you want to attach?" (route to `houmao-specialist-mgr` or `houmao-credential-mgr` depending on whether the credential exists yet)
- "What instance name do you want for the launched managed agent?"

## Guardrails

- Do not pick a tool for the user when multiple tool CLIs are detected; ask.
- Do not mark any detected tool as recommended, preferred, primary, or default.
- Do not attempt to launch when no supported tool CLI is available; explain the supported set instead.
- Do not add background gateway flags unless the user explicitly asked for background or detached gateway execution.
- Do not hand-edit `.houmao/`, runtime, or mailbox paths; route that work through the owning skill.
- Do not restate the concrete command shapes that belong to `houmao-project-mgr`, `houmao-specialist-mgr`, or `houmao-credential-mgr`.
- Do not treat the quickstart branch as the only valid starting branch; the explicit setup branch remains available for users who want the fuller project-and-mailbox path.
