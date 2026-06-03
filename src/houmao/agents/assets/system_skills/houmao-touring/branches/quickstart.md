# Quickstart Branch

Use this beginner branch when the user wants to reach one running managed agent with the minimum number of decisions. This branch is appropriate for a blank-slate workspace or for any caller who explicitly asks for a "quickstart" path.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Detect which supported tool CLIs are available on the host by running a presence check for each tool adapter shipped with the packaged Houmao distribution:
   - `command -v claude`
   - `command -v codex`
   - `command -v gemini`
3. List the detected tool CLIs to the user without priority, without ordering that implies recommendation, and without marking any detected tool as the default or preferred tool. When more than one tool is detected, ask the user which one to use before proceeding.
4. When the workspace has no project overlay, route project initialization through `houmao-project-mgr` first. Do not attempt specialist authoring before the overlay exists.
5. Explain mailbox basics only at the beginner level: the project mailbox root is separate from per-agent mailbox accounts, and per-agent mailbox identity can often be owned by the later launch path.
6. Route credential readiness to `houmao-credential-mgr` when the user needs to inspect, add, update, or log in to a credential before launch.
7. Route specialist authoring, credential selection, and easy-instance launch through `houmao-agent-definition`. Let that skill own the concrete command shapes; this branch only carries the minimum-viable decisions:
   - one specialist name the user can remember (see `references/question-style.md` and `references/concepts.md` for vocabulary),
   - one credential for the chosen tool (API key or locally signed-in credential),
   - one managed-agent instance name for the launch.
8. Advise foreground-first gateway posture for tmux-backed first-run launches in the same way as the rest of the tour; carry that rule into the downstream skill rather than restating the launch flags here.
9. After the first launch succeeds, summarize the new current state and offer stage-aware next actions:
   - talk to the agent through `houmao-agent-messaging`,
   - inspect what is running through `houmao-agent-inspect`,
   - add or read memo context through `houmao-memory-mgr`,
   - try mailbox basics through `houmao-agent-email-comms` when mailbox bindings are ready,
   - enable or inspect mail-notifier posture through `houmao-agent-gateway` when a live gateway and mailbox are ready,
   - create another specialist or launch a second agent,
   - move to advanced loop or workspace guidance only when the user asks for repeated or team coordination.

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
- "What specialist name do you want?" (route to `houmao-agent-definition`; see `references/question-style.md`)
- "Which credential do you want to attach?" (route to `houmao-agent-definition` or `houmao-credential-mgr` depending on whether the credential exists yet)
- "What instance name do you want for the launched managed agent?"

## Guardrails

- Ask the user which tool to use when multiple tool CLIs are detected; do not pick one yourself.
- Do not mark any detected tool as recommended, preferred, primary, or default.
- Explain the supported tool set instead of attempting to launch when no supported tool CLI is available.
- Do not add background gateway flags unless the user explicitly asked for background or detached gateway execution.
- Do not hand-edit `.houmao/`, runtime, or mailbox paths; route that work through the owning skill.
- Leave the concrete command shapes that belong to `houmao-project-mgr`, `houmao-agent-definition`, or `houmao-credential-mgr` on those skills.
- The quickstart branch is not the only valid starting branch; the explicit setup branch remains available for users who want the fuller project-and-mailbox path.
- Offer advanced loop or isolated workspace setup only when coordination intent is emerging or explicit. Do not make it the default next step after the first launch.
