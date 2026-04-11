## Why

The docs site has no page that explains how to choose between the three packaged loop skills (`houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-generic`) or that describes the pairwise-v2 routing-packet prestart model — two things that changed significantly in recent releases. The README also has no mention of `houmao-mgr internals graph`, a first-class CLI command group added in `ec4e25ab`. Readers following the docs cannot discover this surface without reading source code.

## What Changes

- Add `docs/getting-started/loop-authoring.md`: a guide that explains when to choose each of the three loop skills, describes the pairwise-v2 routing-packet prestart model (what routing packets are, how `initialize` uses them, how `graph high packet-expectations` and `validate-packets` help), and introduces `houmao-agent-loop-generic` for mixed pairwise + relay graphs. Includes a skill-selection reference table and links to each skill's SKILL.md and the `internals graph` reference.
- Update `docs/index.md`: add `loop-authoring.md` to the Getting Started section.
- Update the README `## Quick Start` §4 "Agent Loop" section to mention all three loop options and link to the new guide, replacing the current pairwise-only framing.
- Update the README `## CLI Entry Points` table to add an `internals graph` row or note under `houmao-mgr`.

## Capabilities

### New Capabilities

- `docs-loop-authoring-guide`: A getting-started guide for loop plan authoring — skill selection, pairwise-v2 routing-packet model, generic loop graph decomposition, and graph tooling integration.

### Modified Capabilities

- `docs-getting-started`: Add a requirement that the getting-started section links to a loop authoring guide from `docs/index.md`.
- `docs-readme-system-skills`: Add a requirement that the README CLI Entry Points table (or a direct note under `houmao-mgr`) surfaces `houmao-mgr internals graph` as a discoverable CLI command group.

## Impact

- New file: `docs/getting-started/loop-authoring.md`
- Modified files: `docs/index.md`, `README.md`
- Affected specs: `docs-getting-started`, `docs-readme-system-skills` (delta specs), `docs-loop-authoring-guide` (new)
- No runtime code changes.
