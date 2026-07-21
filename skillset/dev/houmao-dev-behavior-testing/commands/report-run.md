# Report a Behavior Qualification Run

## Workflow

1. **Load the frozen run manifest and every planned attempt status.** Keep unexecuted, incomplete, and failed attempts visible.
2. **Verify attempt linkage.** Require case revision, context digest, raw evidence digest, and dimensional verdict for each completed adjudication.
3. **Aggregate each `(case, provider, context)` group** using [../references/verdict-rubric.md](../references/verdict-rubric.md); never use majority vote.
4. **Summarize catalog drift and provider limitations.** Distinguish unsupported, unavailable, and activation-unobservable posture.
5. **Finalize cleanup evidence.** Record removed temporary homes and sessions, preserved run artifacts, and unresolved resources without secret values.
6. **Write `report.json` and `report.md`.** Lead with aggregate outcomes and link every attempt and material evidence path.

If the run contains incomparable case revisions or context definitions, use the native planning tool to partition the report into separate qualification groups rather than merging them.

## Report Contract

Include catalog version, Git revision, Houmao and skill versions, providers/models when observable, context types, attempt counts, dimensional summaries, aggregate status, evidence paths, limitations, drift, and cleanup. A failure is a candidate defect; it does not authorize a runtime-skill edit.

## Guardrails

- DO NOT omit failed or incomplete attempts from totals.
- DO NOT claim full activation qualification for `behavior-pass-activation-unobserved`.
- DO NOT include credentials, secret environment values, or copied auth files in the report.
