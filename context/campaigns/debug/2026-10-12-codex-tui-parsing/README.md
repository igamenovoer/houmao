# Codex TUI Parsing

Determine the appropriate way to parse and track the codex-cli 0.162.x TUI, replacing houmao's stale 0.116.x/0.144.x-era screen-scraping assumptions.

See [debug-intent.md](debug-intent.md) for the complete campaign description.

**Status (2026-10-12)**: iteration 1 complete — KQ-1 resolved, KQ-2 partially answered. The candidate 0.162.x repair (monkey patch under `scripts/explore/codex-tui-parsing/`, no production changes) scores 0.9995/0.9984 on the two user-facing booleans for the lifecycle session and 1.0000/1.0000 for operator surfaces, against blind labels. Integration waits for manual review of [the repair report](reports/2026-10-12-codex-0-162-x-parsing-repair.md) per the campaign's no-product-change declaration.

Sister campaign: [2026-10-10-kimi-code-tui-parsing](../2026-10-10-kimi-code-tui-parsing/) (resolved 2026-10-12; this campaign reuses its methodology, labeling rubric, and recorder workflow).

## Directory Structure

- **debug-intent.md** — Root campaign document with problem statement, scope, boundaries, and status updates
- **key-questions/** — Testable questions with propositions, answers, and scope declarations (KQ-N-<slug>.md)
- **iterations/** — Execution plans with frozen workload, predeclared arms, gates, and checklists (YYYY-MM-DD-plan-N-<slug>.md)
- **evidences/** — Raw capture data from experiments with tables, commands, and environment identity (YYYY-MM-DD-<observation>.md)
- **discussions/** — Analysis and proposal documents with reasoning and design options (YYYY-MM-DD-<topic>.md)
- **reports/** — Theory synthesis and evaluation across multiple evidences (YYYY-MM-DD-<topic>.md)
