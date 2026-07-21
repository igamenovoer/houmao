# Run a Behavior Qualification Suite

## Workflow

1. **Require explicit selection.** Accept `<area>/<profile>`, `<area>/<manual|automatic>/<profile>`, a bare area aliasing `/normal`, `all/<profile>`, `all/<manual|automatic>/<profile>`, `tag:<name>`, exact case or variant ids, or a comma-separated composite union. With no selector, return the read-only suite summary and stop.
2. **Resolve and preview the suite.** Expand cumulative profiles and variants in catalog order, apply invocation-mode filters, deduplicate overlaps, record every selection source and exclusion, and show case, variant, invocation-mode, provider, repetition, and total-attempt counts. Reject unknown selectors before launch.
3. **Invoke `plan-run` once** to freeze selectors, resolved membership, provider/context partitions, attempt matrix, and resource bounds.
4. **Execute cases in isolation.** Use `execute-case` and `adjudicate-case` for each planned attempt without sharing provider conversations.
5. **Preserve dependency and infrastructure failures.** Continue independent cases when safe, but do not convert skipped cases to passes.
6. **Invoke `report-run`** for per-case aggregates, per-area selected and achieved coverage, and suite completion posture.
7. **Return selection, invocation-mode and phase summaries, qualification posture, outcome counts, flaky cases, stable failures, inconclusive cases, activation-unobserved cases, evidence root, and cleanup status.**

If the requested suite mixes admin, managed-agent, missing-dependency, and lifecycle contexts, use the native planning tool to batch only compatible fixture setup while preserving fresh conversation boundaries.

## Guardrails

- DO NOT let one case's response or oracle enter another case's prompt context.
- DO NOT infer a global suite from an absent selector.
- DO NOT claim a selected profile was qualified when required cells remain unexecuted or inconclusive.
- DO NOT call a partial provider matrix complete without listing unsupported or unexecuted cells.
