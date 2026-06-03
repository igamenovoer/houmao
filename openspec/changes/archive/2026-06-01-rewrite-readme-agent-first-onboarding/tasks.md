## 1. README Narrative Rewrite

- [x] 1.1 Audit current README sections, anchors, and docs links that should be preserved or replaced.
- [x] 1.2 Rewrite the Quick Start to show `uv tool install houmao`, `command -v tmux`, preferred `npx skills add igamenovoer/tool-skills/houmao`, the `houmao-mgr system-skills install ...` fallback/custom path, and `$houmao-touring start a guided tour`.
- [x] 1.3 Replace manual numbered usage steps with at least one concise "You:" / "AI:" example showing a CLI agent creating or selecting a specialist, preparing an easy profile, launching a managed agent, and sending an initial gateway-backed prompt.
- [x] 1.4 Add or revise the core concepts section so it explains user CLI agent, specialist, easy profile, managed agent, gateway, mailbox, and loop from the user's mental model.

## 2. Loop And Advanced Workflow Positioning

- [x] 2.1 Rewrite the agent-loop section so `houmao-agent-loop-pro` is the primary complex-plan story: intention/execplan decomposition, preparation, validation, launch, run control, and operator observation from outside the loop.
- [x] 2.2 Mention `houmao-agent-loop-lite` as the lightweight Markdown/direct-SQL path without making it replace the pro loop as the main complex-plan example.
- [x] 2.3 Keep the writer-team example discoverable as a reusable example/template, but remove command-heavy tutorial material from the main README path.

## 3. Reference Compression

- [x] 3.1 Compress System Skills into a short agent-capability summary and link to the System Skills Overview for the full catalog and boundaries.
- [x] 3.2 Move or replace long inline command-reference material for project init, specialist flags, `agents join`, raw profiles/recipes, managed-header details, demos, and CLI entrypoints with concise summaries and docs links.
- [x] 3.3 Verify README no longer recommends the full Houmao source-tree `system_skills/` path as the ordinary `npx` installation target.

## 4. Tests And Validation

- [x] 4.1 Update README/documentation tests that assert old heading order, numbered Quick Start steps, command snippets, or skill-install wording.
- [x] 4.2 Run the focused README/docs tests that cover README structure and getting-started links.
- [x] 4.3 Run `openspec validate rewrite-readme-agent-first-onboarding --strict` and confirm the change is apply-ready.
