## Why

The current quickstart still teaches Houmao as a sequence of manual `houmao-mgr` commands, while the README and system-skills guide now define the normal user experience as agent-driven: the user's Claude Code, Codex, Gemini, or similar CLI agent reads Houmao system skills and runs the maintained CLI surfaces on the user's behalf.

This mismatch makes the first docs path feel like an operator shell tutorial instead of the product's intended agentic workflow.

## What Changes

- Reframe `docs/getting-started/quickstart.md` around agent-driven use as the primary path: install Houmao, install Houmao system skills into the user's CLI-agent home, start the CLI agent in the target project, and invoke `houmao-touring`.
- Replace the current command-first lifecycle flow with a first useful agent prompt that creates or selects a specialist, prepares a reusable project profile when useful, launches a managed agent, prompts it, inspects the result, and stops it.
- Explain the underlying Houmao work as concepts and outcomes: project overlay, specialist, project profile, managed agent, gateway, messaging, inspection, memory, mailbox, and loop follow-up.
- Keep direct CLI command examples as manual fallback, source-checkout translation, or troubleshooting material rather than the first-run narrative.
- Preserve `agents self join` as the documented path for adopting an already-running provider TUI, but position it as a secondary adoption workflow rather than the main first-run experience.
- Align quickstart cross-links and docs index wording with the agent-driven entrypoint.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `docs-getting-started`: Revise the quickstart requirements so the primary getting-started path is agent-driven through installed Houmao system skills and `houmao-touring`, with manual command sequences demoted to fallback or reference material.
- `docs-site-structure`: Update docs index requirements if needed so the quickstart entry is described as the agent-driven first-run guide rather than a manual build-brain command walkthrough.

## Impact

- Affected docs: `docs/getting-started/quickstart.md`, likely `docs/index.md`, and possibly adjacent getting-started cross-links.
- Affected specs: `openspec/specs/docs-getting-started/spec.md` delta and a small `docs-site-structure` delta if index wording changes.
- No runtime code, CLI behavior, package dependencies, migrations, or API surfaces are affected.
