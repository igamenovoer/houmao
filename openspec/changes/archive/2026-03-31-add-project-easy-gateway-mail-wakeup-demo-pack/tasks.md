## 1. Pack Scaffolding

- [x] 1.1 Create the supported demo under `scripts/demo/single-agent-mail-wakeup/` with a runner, README, tracked inputs, and a demo-local ignore policy for generated output roots.
- [x] 1.2 Add demo implementation modules under `src/houmao/demo/` for the new demo, reusing legacy single-agent wake-up patterns only where they still match the new project-easy contract.
- [x] 1.3 Define the demo output layout so each tool lane owns a copied `project/` root, redirected `overlay/` root, and demo-owned `control/`, `logs/`, `deliveries/`, and `evidence/` directories.

## 2. Project-Easy Wake-Up Workflow

- [x] 2.1 Implement command helpers that always run project-aware commands from the copied project root while exporting `HOUMAO_PROJECT_OVERLAY_DIR` to the sibling redirected overlay root.
- [x] 2.2 Implement Claude Code and Codex TUI preflight/setup for project-local auth import, specialist creation, project mailbox bootstrap, mailbox registration, and `project easy instance launch`.
- [x] 2.3 Implement gateway attach, notifier enablement, operator-message delivery, readiness/wait logic, and stepwise commands (`start`, `manual-send`, `inspect`, `verify`, `stop`, `auto`, `matrix`) for the single-agent workflow.

## 3. Verification And Supported Surface

- [x] 3.1 Implement the demo verification/report contract around gateway notifier evidence, artifact creation under `<output-root>/project/tmp/`, actor-scoped `agents mail check --unread-only`, and structural `project mailbox messages list|get` corroboration.
- [x] 3.2 Add automated coverage for the new demo's layout, command surface, and verification/report contract.
- [x] 3.3 Update `scripts/demo/README.md` and the new demo README so the maintained demo surface documents the supported project-easy gateway mail wake-up workflow and its Claude/Codex TUI lanes.
