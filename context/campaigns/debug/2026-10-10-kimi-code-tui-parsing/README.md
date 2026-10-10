# Kimi Code TUI Parsing

Determine the appropriate way to parse and track the kimi-code 2.1.x TUI, replacing houmao's stale 0.11.x/0.23.x-era screen-scraping assumptions.

See [debug-intent.md](debug-intent.md) for the complete campaign description.

## Directory Structure

- **debug-intent.md** — Root campaign document with problem statement, scope, boundaries, and status updates
- **key-questions/** — Testable questions with propositions, answers, and scope declarations (KQ-N-<slug>.md)
- **iterations/** — Execution plans with frozen workload, predeclared arms, gates, and checklists (YYYY-MM-DD-plan-N-<slug>.md)
- **evidences/** — Raw capture data from experiments with tables, commands, and environment identity (YYYY-MM-DD-<observation>.md)
- **reports/** — Theory synthesis and evaluation across multiple evidences (YYYY-MM-DD-<topic>.md)
