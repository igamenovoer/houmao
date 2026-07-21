# Report a Behavior Qualification Run

## Workflow

1. **Load frozen selection and every planned attempt status.** Keep requested selectors, resolved cases and variants, exclusions, unexecuted, incomplete, and failed attempts visible.
2. **Verify attempt linkage.** Require case revision, variant id, context digest, raw evidence digest, and dimensional verdict for each completed adjudication.
3. **Aggregate each `(case, variant, provider, context)` group** using [../references/verdict-rubric.md](../references/verdict-rubric.md); never use majority vote.
4. **Determine qualification posture.** Use `selection-only` when no attempts ran, `partial qualification` when required cells are unexecuted or inconclusive, and `full qualification` only when every required planned cell has a judgeable aggregate. Keep pass, flaky, and fail outcomes separate from this completion posture.
5. **Summarize per-area coverage, catalog drift, and provider limitations.** Report selected profile, resolved case and variant counts, planned and completed cells, and unsupported, unavailable, or activation-unobservable posture.
6. **Finalize cleanup evidence.** Record removed temporary homes and sessions, preserved run artifacts, and unresolved resources without secret values.
7. **Write `report.json` and `report.md`.** Lead with selectors, qualification posture, aggregate outcomes, and links to every attempt and material evidence path.

If the run contains incomparable case revisions or context definitions, use the native planning tool to partition the report into separate qualification groups rather than merging them.

## Report Contract

Include requested selectors, catalog version and digest, resolved case and variant counts, area/profile attribution, Git revision, Houmao and skill versions, providers/models when observable, context types, planned and completed attempt counts, qualification posture, dimensional summaries, aggregate status, evidence paths, limitations, drift, and cleanup. A failure is a candidate defect; it does not authorize a runtime-skill edit.

## Guardrails

- DO NOT omit failed or incomplete attempts from totals.
- DO NOT describe selected coverage as qualified when required cells are unexecuted or inconclusive.
- DO NOT claim full activation qualification for `behavior-pass-activation-unobserved`.
- DO NOT include credentials, secret environment values, or copied auth files in the report.
