## Context

The README currently serves as both entry point and reference manual. Sections 2–3 reproduce the full agent-definition-directory tree and adapter.yaml/preset/auth semantics that already live in `docs/getting-started/agent-definitions.md` and `docs/reference/agents/operations/project-aware-operations.md`. Section 5 duplicates the server-pair workflow from `docs/reference/houmao_server_pair.md`. The architecture mermaid diagrams duplicate `docs/getting-started/overview.md`. Meanwhile, two important user-facing workflows — easy specialists and runnable demos — are not represented at all.

The project introduction (status, "What It Is", "The Core Idea", benefits, typical use cases, "How Agents Join Your Workflow") is explicitly out of scope for this change per the user's direction.

## Goals / Non-Goals

**Goals:**

- Cut README from ~500 to ~250 lines by removing content that is already in docs/.
- Present a clear progressive-disclosure ladder: `agents join` → `project easy specialist` → full preset launch.
- Surface the two runnable demos as worked examples.
- Add brief "Subsystems at a Glance" pointers to gateway, mailbox, and TUI tracking.
- Make GitHub Pages the canonical destination for deep dives.

**Non-Goals:**

- Rewriting or modifying the project introduction sections (status, "What It Is", "The Core Idea", benefits, typical use cases, "How Agents Join Your Workflow").
- Changing any docs/ content.
- Changing any source code.
- Adding new docs pages.

## Decisions

### 1. Keep `agents join` section (§1) intact

The current §1 including the mermaid sequence diagram, step-by-step commands, and "What You Get After Joining" capability table is the best part of the README. Keep it as-is — it already follows the progressive-disclosure pattern (show the simplest path first).

**Alternative considered:** Trimming the mermaid diagram. Rejected because it renders well on GitHub and gives a clear visual of what `agents join` does.

### 2. New "Easy Specialists" section replaces §2–§3

Instead of the full agent-definition-directory layout, show the `project easy specialist` workflow as the natural next step after `agents join`. This covers `project init` → `specialist create` → `instance launch` → prompt → stop in a compact code block. Verify the exact CLI flags from the Click commands before writing.

**Alternative considered:** Keeping a trimmed version of the agent-def-dir layout. Rejected because it's reference material that belongs in docs, and the easy-specialist path is what most users want.

### 3. Slim "Full Preset Launch" replaces §4

Keep a brief 5-line code example of `agents launch` from a preset, plus a link to `docs/getting-started/agent-definitions.md` and the `scripts/demo/minimal-agent-launch/` demo. No more adapter.yaml/auth/preset schema.

### 4. New "Runnable Demos" section

Two entries:

- `scripts/demo/minimal-agent-launch/` — brief description + run command. Link to its spec for details.
- `scripts/demo/single-agent-mail-wakeup/` — brief description + run command. Link to its README for details.

### 5. New "Subsystems at a Glance" section

One-liner descriptions with links to docs/ pages:

- Gateway — per-agent sidecar for session control and mail
- Mailbox — unified protocol for filesystem and Stalwart JMAP
- TUI Tracking — state machine, detectors, and replay engine

### 6. Remove §5 (server-backed multi-agent) and architecture diagrams

Already in docs. The README just needs a "Full Documentation" link to `https://igamenovoer.github.io/houmao/`.

### 7. Shrink Legacy CAO to a footnote

One sentence noting it existed and pointing to docs if needed.

### 8. Trim Installation

Drop the pg-hosting optional block (it's a future/optional concern). Keep pixi + tmux. Drop standalone docs-build section; fold `pixi run docs-serve` into the Development section.

## Risks / Trade-offs

- **Removing content from README reduces discoverability for users who don't visit docs** → Mitigated by explicit "Full Documentation" link and brief subsystem pointers.
- **Easy specialist CLI flags may change** → Verify from actual Click command definitions before writing the section. The easy specialist CLI is under active development.
- **Mermaid diagrams don't render everywhere** → Keeping the `agents join` diagram since GitHub renders it; not adding new ones.
