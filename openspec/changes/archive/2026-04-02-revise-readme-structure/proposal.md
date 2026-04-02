## Why

The project README currently duplicates reference material that already lives in the docs site — full agent-definition-directory layouts, adapter.yaml schemas, auth bundle conventions, architecture mermaid diagrams, and server-pair workflows. This makes the README ~500 lines and overwhelming for first-time readers. Meanwhile, the README lacks coverage of two important user-facing workflows: easy specialists (`houmao-mgr project easy`) and the runnable demos (`scripts/demo/`). The README should be a concise entry point that shows the progressive-disclosure ladder (join → easy → full preset) and points to GitHub Pages for everything else.

## What Changes

- **Remove sections 2–3** (project init details + full agent-definition-directory layout) — this content is already in `docs/getting-started/agent-definitions.md` and `docs/reference/agents/operations/project-aware-operations.md`.
- **Remove section 5** (server-backed multi-agent coordination) — already in `docs/reference/houmao_server_pair.md`.
- **Remove Developer Guide / Architecture section** (mermaid diagrams) — already in `docs/getting-started/overview.md`.
- **Shrink Legacy CAO appendix** to a one-line footnote.
- **Keep section 1** (`agents join` quick start) essentially unchanged — it's the best part of the current README.
- **Add new "Easy Specialists" section** showing `project easy specialist create` → `instance launch` → `instance stop` flow.
- **Slim section 4** (basic workflow) into a brief "Full Preset Launch" summary with link to docs + demo.
- **Add new "Runnable Demos" section** pointing to `scripts/demo/minimal-agent-launch/` and `scripts/demo/single-agent-mail-wakeup/`.
- **Add new "Subsystems at a Glance" section** with brief one-liner pointers to gateway, mailbox, and TUI tracking docs.
- **Add explicit "Full Documentation" section** pointing to the GitHub Pages URL.
- **Keep the Project Introduction unchanged** (status, what it is, core idea, benefits, typical use cases, how agents join your workflow).
- **Trim Installation** to drop the optional pg-hosting block.
- **Drop the standalone Documentation/mkdocs build section** — fold a one-liner into Development.

## Capabilities

### New Capabilities

- `readme-easy-specialist-section`: New README section demonstrating the `project easy specialist` workflow as a middle path between `agents join` and full preset launch.
- `readme-runnable-demos-section`: New README section surfacing the two maintained runnable demos with brief descriptions and run commands.
- `readme-subsystems-glance`: New README section with brief pointers to gateway, mailbox, and TUI tracking docs on GitHub Pages.

### Modified Capabilities

- `docs-site-structure`: The README restructuring changes the entry-point flow and cross-links to the docs site. The site index may need a reciprocal "back from README" reference.

## Impact

- `README.md` — primary target; approximately halved from ~500 to ~250 lines.
- No source code changes.
- No docs/ content changes (content already exists there).
- Cross-links from README to docs/ pages and GitHub Pages URL.
