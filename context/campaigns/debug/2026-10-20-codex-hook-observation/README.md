# Codex Hook Observation

Validate, through captured live evidence and throwaway implementation experiments, that a Codex hook observation channel can be built for houmao: hooks injected through the runtime-owned home, **auto-trusted with zero user action in unattended mode**, payload catalog of the 14 Codex events confirmed at the installed version, and the merged hook + TUI state-transition rules reproduced against real paired streams before any production code is written.

See [debug-intent.md](debug-intent.md) for the complete campaign description.

## Directory Structure

- **debug-intent.md** — Root campaign document with problem statement, scope, boundaries, and status updates
- **key-questions/** — Testable questions with propositions, answers, and scope declarations (KQ-N-<slug>.md)
- **iterations/** — Execution plans with frozen workload, predeclared arms, gates, and checklists (YYYY-MM-DD-plan-N-<slug>.md)
- **evidences/** — Raw measurement data from experiments with tables, commands, and hardware identity (YYYY-MM-DD-<observation>.md)
- **discussions/** — Analysis and proposal documents with reasoning and design options (YYYY-MM-DD-<topic>.md)
- **reports/** — Theory synthesis and evaluation across multiple evidences (YYYY-MM-DD-<topic>.md)

## Experiment Code

Throwaway implementation experiments (collector variants, emitter, normalizer, posture reducer, merge replay) live in `scripts/explore/codex-hook-observation/`. Nothing there is production code; promotion into `src/` happens only through a future OpenSpec change after the campaign resolves.
