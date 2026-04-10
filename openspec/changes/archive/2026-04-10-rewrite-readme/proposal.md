## Why

The current README leads with `agents join` as the recommended starting point, but the actual recommended workflow has shifted to: install system skills, initialize a project, create specialists/profiles, and launch agents. The README also has no coverage of agent loops (pairwise/relay coordination), which is a flagship multi-agent capability. Users arriving at the README get an outdated impression of how Houmao is meant to be used.

## What Changes

- **Restructure the Quick Start flow**: Lead with system-skills install as step 0, project init as step 1, specialist creation + launch as step 2 (primary path). Move `agents join` to a secondary "lightweight/ad-hoc" section.
- **Add Agent Loop section**: New section showcasing multi-agent coordination via `houmao-agent-loop-pairwise`, using the agentsys2 story-writing example (3 specialists, per-chapter pipeline, mermaid control graph, produced artifacts).
- **Condense the intro**: Merge "What It Is" / "Core Idea" / "What The Framework Provides" / "Why This Is Useful" into two tighter sections, shifting emphasis from join-first to specialist-first.
- **Add system-skills install prerequisite**: Explain that without system skills installed, agents cannot self-manage through their native skill interface.
- **Add houmao project introduction**: Explain `project init` and the `.houmao/` overlay as the scaffolding that holds specialists, profiles, credentials, and mailbox together.

## Capabilities

### New Capabilities

- `readme-structure`: The new README section layout, ordering, and content outline covering the specialist-first quick start, agent loop showcase, and repositioned join path.

### Modified Capabilities

(none - this is a documentation-only change with no spec-level behavior modifications)

## Impact

- `README.md` — full rewrite
- No code, API, or dependency changes
- No changes to CLI behavior or system skills
- Published docs site is unaffected (README is the repo landing page, not part of the mkdocs site)
