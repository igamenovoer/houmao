## 1. Audit Current Docs

- [x] 1.1 Review `docs/getting-started/quickstart.md` and identify command-first sections to keep, move, shorten, or remove.
- [x] 1.2 Review `README.md`, `docs/getting-started/system-skills-overview.md`, `docs/getting-started/easy-specialists.md`, and `docs/getting-started/launch-profiles.md` for agent-driven wording and cross-link targets to reuse.
- [x] 1.3 Confirm the maintained command surfaces named in the quickstart fallback sections still match `docs/reference/cli/` coverage and current project guidance.

## 2. Rewrite Quickstart Around Agent-Driven Use

- [x] 2.1 Replace the current quickstart opening with the user-agent mental model, installed-user setup path, system-skill installation choices, and source-checkout launcher translation note.
- [x] 2.2 Add the primary agent-driven first-run workflow: start the CLI agent in the target project, invoke `$houmao-touring start a guided tour`, and use a first useful outcome prompt.
- [x] 2.3 Explain expected Houmao outcomes in user-facing terms: `.houmao/` project overlay, specialist, project profile, managed agent, gateway, messaging, inspection, memory, mailbox, and loop follow-up.
- [x] 2.4 Add compact "what the agent may run" or manual fallback command examples for project setup, specialist/profile preparation, launch, prompt or gateway messaging, inspection, stop, and system-skill installation.

## 3. Preserve Secondary Workflows and Cross-Links

- [x] 3.1 Reposition `agents self join` as the secondary adoption workflow for an already-running provider TUI while preserving a complete join-to-control-to-stop path.
- [x] 3.2 Keep or revise the join Mermaid diagram so it still shows provider TUI adoption into managed-agent artifacts, gateway, and registry visibility.
- [x] 3.3 Update quickstart next links and in-page references to point to System Skills Overview, Easy Specialists, Launch Profiles, Managed Agent Memory, gateway/mailbox references, and CLI reference pages.
- [x] 3.4 Update `docs/index.md` wording so the quickstart is described as the agent-driven first-run guide with source-checkout launcher notes.

## 4. Verification

- [x] 4.1 Check the revised quickstart for removed or retired surface names, including `houmao-cli`, standalone `houmao-server`, standalone CAO launcher workflows, `agents terminate`, and manual `.agentsys` setup.
- [x] 4.2 Run a link/path sanity check for all changed Markdown links.
- [x] 4.3 Run `pixi run format` only if implementation touches formatted source files; otherwise skip and record why.
- [x] 4.4 Run OpenSpec validation or status checks for `revise-agent-driven-quickstart` and confirm the change remains apply-ready.
