## 1. New Reference Page

- [x] 1.1 Create `docs/reference/cli/internals.md` with an introduction section explaining the `internals` command group purpose and when to use it.
- [x] 1.2 Add a `## graph high` section to `internals.md` with descriptions and full option tables for `analyze`, `packet-expectations`, `validate-packets`, `slice`, and `render-mermaid`, each with at least one usage example.
- [x] 1.3 Add a `## graph low` section to `internals.md` with descriptions and key option tables for `create`, `mutate`, `relabel`, `compose`, `subgraph`, `reverse`, and `ego`.
- [x] 1.4 Add a `## graph low alg` section to `internals.md` with the shared option schema table and a summary table of all 13 algorithm subcommands.
- [x] 1.5 Add a brief context paragraph explaining when `graph high` is preferred (loop plan authoring and validation) versus `graph low` (generic graph construction and NetworkX algorithm access).

## 2. Update houmao-mgr.md

- [x] 2.1 Add a `### internals — Internal utility commands` section to `docs/reference/cli/houmao-mgr.md` that describes the group purpose and links to `internals.md` for the full reference.

## 3. Update docs/index.md

- [x] 3.1 Add an `internals` link entry to the CLI surfaces section of `docs/index.md`, pointing to `reference/cli/internals.md`.

## 4. Update system-skills-overview.md

- [x] 4.1 Add a brief "Graph Tooling" note to the loop-skills section of `docs/getting-started/system-skills-overview.md` explaining that `houmao-mgr internals graph high` (`analyze`, `packet-expectations`, `validate-packets`, `slice`, `render-mermaid`) is available as a deterministic structural helper for `houmao-agent-loop-pairwise-v2` and `houmao-agent-loop-generic` authoring, with a link to `docs/reference/cli/internals.md`.

## 5. Sync Specs to Main

- [x] 5.1 Sync the new `docs-internals-graph-cli-reference` delta spec to `openspec/specs/docs-internals-graph-cli-reference/spec.md`.
- [x] 5.2 Merge the `docs-cli-reference` MODIFIED requirement into `openspec/specs/docs-cli-reference/spec.md`.

## 6. Verification

- [x] 6.1 Run `pixi run openspec validate document-internals-graph-cli --strict` and confirm no errors.
- [x] 6.2 Verify `docs/reference/cli/internals.md` exists and the option tables match the current live CLI flags in `src/houmao/srv_ctrl/commands/internals.py`.
- [x] 6.3 Verify `docs/index.md` links to `internals.md` and `docs/reference/cli/houmao-mgr.md` has the new `### internals` section.
- [x] 6.4 Verify `docs/getting-started/system-skills-overview.md` loop-skills section includes the graph-tooling note and link.
