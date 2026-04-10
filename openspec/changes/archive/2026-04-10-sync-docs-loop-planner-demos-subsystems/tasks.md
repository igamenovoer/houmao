## 1. README — System Skills Table and user-control Set

- [x] 1.1 Add a `houmao-loop-planner` row to the README system-skills table (after `houmao-agent-definition`, before `houmao-agent-instance`). Description: "Author operator-owned loop bundles, prepare participant and distribution guidance, and prepare runtime handoff for pairwise or relay loops. Manual invocation only."
- [x] 1.2 Update the README paragraph that lists `user-control` set members to include `houmao-loop-planner` alongside the existing six members (total: 7).
- [x] 1.3 Verify the README skill count narrative matches the catalog (15 skills total).

## 2. README — Runnable Demos

- [x] 2.1 Add a `shared-tui-tracking-demo-pack/` entry to the "Runnable Demos" section. Source the description from `scripts/demo/README.md`. Include a runner command.
- [x] 2.2 Add a `single-agent-gateway-wakeup-headless/` entry to the "Runnable Demos" section. Source the description from `scripts/demo/README.md`. Include a runner command.

## 3. README — Subsystems at a Glance

- [x] 3.1 Add a `Passive Server` row to the "Subsystems at a Glance" table. Description: "Registry-driven stateless server for distributed agent coordination — no child-process supervision." Link to `docs/reference/cli/houmao-passive-server.md`.

## 4. Getting-Started — System Skills Overview

- [x] 4.1 Add `houmao-loop-planner` to the "Loop authoring and master-run control" concern group in `docs/getting-started/system-skills-overview.md`. Include skill name, brief description, canonical CLI routing, and note that it is manual-invocation-only.
- [x] 4.2 Verify the overview guide skill count and auto-install set expansion match the current `catalog.toml` (15 skills; `user-control` set has 7 members).

## 5. Validation

- [x] 5.1 Run `pixi run docs-serve` or `pixi run python -m mkdocs build --strict` to confirm no broken links or build errors.
- [x] 5.2 Visually confirm the README system-skills table has 15 rows, the demos section has 4 entries, and the subsystems table has 4 rows.
