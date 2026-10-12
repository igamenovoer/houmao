# Claude Code TUI Parsing

Determine how houmao should parse Claude Code 2.1.296 TUI surfaces to decide the two user-facing booleans (ready to enter prompt, accept prompt), given that the maintained `2.1.x` detector was qualified around 2.1.81 and the installed binary is a closed-source bun executable reachable only through the cost-metered OpenLux relay.

See [debug-intent.md](debug-intent.md) for the complete campaign description.

## Directory Structure

- **debug-intent.md** — Root campaign document with problem statement, scope, boundaries, and status updates
- **key-questions/** — Testable questions with propositions, answers, and scope declarations (KQ-N-<slug>.md)
- **iterations/** — Execution plans with frozen workload, predeclared arms, gates, and checklists (YYYY-MM-DD-plan-N-<slug>.md)
- **evidences/** — Raw measurement data from experiments with tables, commands, and hardware identity (YYYY-MM-DD-<observation>.md)
- **discussions/** — Analysis and proposal documents with reasoning and design options (YYYY-MM-DD-<topic>.md)
- **reports/** — Theory synthesis and evaluation across multiple evidences (YYYY-MM-DD-<topic>.md)

## Sibling Campaigns

- [2026-10-10-kimi-code-tui-parsing](../2026-10-10-kimi-code-tui-parsing/) — established the record-first, blind-label methodology this campaign reuses.
- [2026-10-12-codex-tui-parsing](../2026-10-12-codex-tui-parsing/) — refined the methodology (promptfoo session contracts, qualification thresholds) and produced the registry posture this campaign evaluates for claude.
