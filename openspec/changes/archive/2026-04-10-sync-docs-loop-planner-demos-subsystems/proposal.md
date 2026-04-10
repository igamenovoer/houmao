## Why

Recent feature commits (v0.4.2 → v0.5.0) added the `houmao-loop-planner` system skill to the catalog and the `user-control` auto-install set, shipped two new maintained demos (`single-agent-gateway-wakeup-headless`, `shared-tui-tracking-demo-pack`), and stabilized `houmao-passive-server` as a documented CLI entrypoint — but the project `README.md` and the `docs/getting-started/system-skills-overview.md` guide were not updated to reflect these additions. Readers of the two highest-traffic discovery surfaces therefore see an incomplete skill catalog (14 of 15 skills), a stale demo index (2 of 4 maintained demos), and a subsystems table that omits the passive-server.

## What Changes

- Add a `houmao-loop-planner` row to the README system-skills table and mention it in the `user-control` set description paragraph.
- Add `houmao-loop-planner` to the `docs/getting-started/system-skills-overview.md` narrative guide in the "Loop authoring and master-run control" concern group.
- Add `single-agent-gateway-wakeup-headless/` and `shared-tui-tracking-demo-pack/` to the README "Runnable Demos" section.
- Add a `Passive Server` row to the README "Subsystems at a Glance" table with a link to `docs/reference/cli/houmao-passive-server.md`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `docs-readme-system-skills`: Add `houmao-loop-planner` to the README skill table and update the `user-control` set enumeration from 6 to 7 members.
- `docs-system-skills-overview-guide`: Add `houmao-loop-planner` to the narrative guide's skill catalog and the "Loop authoring and master-run control" concern group.

## Impact

- `README.md` — four edits: skills table row, user-control set paragraph, demos section, subsystems table.
- `docs/getting-started/system-skills-overview.md` — one edit: loop-planner entry added.
- No code, API, or dependency changes.
