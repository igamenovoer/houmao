## Context

The `docs/` tree was last substantially refreshed on March 31, 2026 (commit `b6cfb71`). Since then, several user-facing features shipped without corresponding documentation: gateway mail-notifier API revisions, native project mailbox skills for Claude, and project-aware operations. Additionally, ~5 CLI reference pages remain as truncated stubs from the prior doc pass, and the houmao-passive-server page is a 30-line placeholder.

The existing OpenSpec spec suite already has detailed requirements for docs-cli-reference, docs-getting-started, docs-site-structure, docs-stale-content-removal, and several subsystem reference specs. This change extends that coverage to newly shipped features and completes the stub pages.

## Goals / Non-Goals

**Goals:**

- Complete all truncated CLI reference stubs so every `houmao-mgr` subcommand has full option tables and usage notes.
- Add conceptual documentation for the gateway mail-notifier, project-aware operations, project mailbox skills, easy-specialist model, and launch policy engine.
- Rewrite the houmao-passive-server reference page with operational depth.
- Polish the quickstart to be end-to-end complete for both workflows.
- Sweep stale "agentsys" references from all docs.
- Update index pages to link all new pages.

**Non-Goals:**

- Rewriting developer-internals docs (`developer/tui-parsing/`, `developer/houmao-server/`, `developer/terminal-record/`) — these are internal and lower priority.
- Adding tutorial/demo documentation for `single_agent_mail_wakeup` — the demo itself has inline comments; a tutorial can come later.
- Restructuring the docs site hierarchy (merging `developer/` into `reference/*/internals/`) — this is a separate structural change.
- Auto-generating CLI reference from `--help` output — hand-written docs with examples are the established pattern.

## Decisions

### D1: Content derivation strategy — source code + CLI help, not reverse-engineering

All new documentation content will be derived from:
1. Module-level and class-level docstrings in the relevant source files.
2. Click decorator help text and parameter descriptions from `srv_ctrl/commands/`.
3. Live `houmao-mgr <command> --help` output for option tables.
4. Existing related docs for cross-referencing.

**Rationale:** This matches the established pattern in existing complete docs (e.g., `admin-cleanup.md`, `launch-overrides.md`) and ensures accuracy without guessing.

### D2: New pages go under `docs/reference/` following existing structure

| New page | Location |
|----------|----------|
| Gateway mail-notifier | `docs/reference/gateway/operations/mail-notifier.md` |
| Project-aware operations | `docs/reference/agents/operations/project-aware-operations.md` |
| Project mailbox skills | `docs/reference/mailbox/contracts/project-mailbox-skills.md` |
| Easy-specialist guide | `docs/getting-started/easy-specialists.md` |
| Launch policy reference | `docs/reference/build-phase/launch-policy.md` |

**Rationale:** Follows the existing directory structure and naming conventions. Gateway mail-notifier sits naturally under `gateway/operations/`. Project-aware ops is an agent operations concern. Mailbox skills is a mailbox contract. Easy-specialist is a getting-started concept. Launch policy is a build-phase reference.

### D3: Stub completion uses the same hand-written style as existing complete pages

The truncated pages (`agents-gateway.md`, `agents-mail.md`, `agents-mailbox.md`, `agents-turn.md`) will be completed in the same style as `admin-cleanup.md` — hand-written prose with option tables, not auto-generated from `--help`.

**Rationale:** Consistent style across the CLI reference section. Auto-generation would create a different reading experience and would require tooling that doesn't exist yet.

### D4: houmao-passive-server rewrite covers comparison with houmao-server

The rewritten page will include a "When to use which server" comparison table contrasting passive-server (stateless, registry-driven, no child process management) vs houmao-server (stateful, CAO-compatible, full session supervision).

**Rationale:** This is the primary operator question when choosing between the two servers.

### D5: "agentsys" sweep is mechanical grep-and-replace

Any remaining `agentsys` references in `docs/` will be replaced with `houmao` equivalents. This includes path references (`.agentsys/` → `.houmao/`), variable names (`AGENTSYS_*` → `HOUMAO_*`), and prose mentions.

**Rationale:** The rename happened in `b5b616f` and is a straightforward find-and-replace with manual review for context accuracy.

## Risks / Trade-offs

- **[Docs drift quickly]** → The codebase is under active development. To mitigate, docs will reference stable abstractions (CLI command surface, config models) rather than internal implementation details that change frequently.
- **[Large surface area]** → ~15 files modified, ~5 new. To mitigate, tasks are structured so each page is independently completable and reviewable.
- **[Spec fidelity]** → Existing specs are detailed and prescriptive. New delta specs will be written at the same level of detail to maintain consistency.
