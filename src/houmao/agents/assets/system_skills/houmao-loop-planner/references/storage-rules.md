# Storage Rules

Use this reference when the user asks where the loop bundle should live and what it should avoid.

## Rules

- Write the authored bundle in a user-designated directory.
- Keep the bundle static and operator-owned.
- Do not write the authored bundle into `HOUMAO_JOB_DIR` or `HOUMAO_MEMORY_DIR`.
- Do not treat the authored bundle as mutable runtime scratch or as a long-term runtime ledger.
- Keep distribution as an operator action rather than as hidden planner-owned state changes.
