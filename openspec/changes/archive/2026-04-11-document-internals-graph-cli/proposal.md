## Why

The `houmao-mgr internals graph` command group was added in the `add-internals-graph-tools` change but has no documentation on the docs site — no reference page, no entry in `houmao-mgr.md`, and no link from `docs/index.md`. The `docs-cli-reference` spec also predates this command group and does not require it. Readers and agents relying on the docs site cannot discover this surface without reading source code.

## What Changes

- Add a dedicated reference page `docs/reference/cli/internals.md` covering `houmao-mgr internals graph high` and `graph low` subcommands, their inputs/outputs, and usage context for loop authoring.
- Add an `### internals` section to `docs/reference/cli/houmao-mgr.md` linking to the new page.
- Add a `internals` entry to the CLI surfaces section of `docs/index.md`.
- Update `docs/getting-started/system-skills-overview.md` to note that `houmao-mgr internals graph` tooling is available to support `houmao-agent-loop-pairwise-v2` and `houmao-agent-loop-generic` authoring.
- Update the `docs-cli-reference` spec to require `internals` in the documented command group list.

## Capabilities

### New Capabilities

- `docs-internals-graph-cli-reference`: The docs site reference page for `houmao-mgr internals graph high` and `graph low` — command summaries, input/output format, subcommand tables, and loop-authoring context.

### Modified Capabilities

- `docs-cli-reference`: The `houmao-mgr` CLI reference spec must require `internals` as a documented top-level command group alongside `admin`, `agents`, `brains`, `credentials`, `mailbox`, `project`, and `server`.

## Impact

- Affected docs files:
  - `docs/reference/cli/internals.md` (new)
  - `docs/reference/cli/houmao-mgr.md` (add internals section)
  - `docs/index.md` (add internals link)
  - `docs/getting-started/system-skills-overview.md` (add graph tooling note)
- Affected specs:
  - `openspec/specs/docs-cli-reference/spec.md` (add internals requirement)
  - `openspec/specs/docs-internals-graph-cli-reference/spec.md` (new)
- No runtime code changes.
