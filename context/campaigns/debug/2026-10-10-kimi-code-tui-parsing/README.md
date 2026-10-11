# Kimi Code TUI Parsing

Determine the appropriate way to parse and track the kimi-code 2.1.x TUI, replacing houmao's stale 0.11.x/0.23.x-era screen-scraping assumptions.

See [debug-intent.md](debug-intent.md) for the complete campaign description.

**Resolution (2026-10-12)**: KQ-1 resolved, KQ-2 closed, KQ-3 unopened. The repaired text-scraping approach (Arm A) landed in production via `openspec/changes/raise-kimi-code-floor-2-1-1/`: kimi-code support is floor-gated at 2.1.1, `KimiCodeSignalDetectorV2_1_X` carries the campaign's measured repairs, and `tests/unit/shared_tui_tracking/test_kimi_code_2_1_x_qualification.py` replays both frozen sessions as a standing gate (zero false-ready/false-busy, 100%/100% on the two admission booleans). The campaign tooling under `scripts/explore/kimi-code-tui-parsing/` is preserved as experiment record; its monkey patch targets the pre-change seams and is superseded by the production detector — do not rerun it against current `src/`.

## Directory Structure

- **debug-intent.md** — Root campaign document with problem statement, scope, boundaries, and status updates
- **key-questions/** — Testable questions with propositions, answers, and scope declarations (KQ-N-<slug>.md)
- **iterations/** — Execution plans with frozen workload, predeclared arms, gates, and checklists (YYYY-MM-DD-plan-N-<slug>.md)
- **evidences/** — Raw capture data from experiments with tables, commands, and environment identity (YYYY-MM-DD-<observation>.md)
- **reports/** — Theory synthesis and evaluation across multiple evidences (YYYY-MM-DD-<topic>.md)
