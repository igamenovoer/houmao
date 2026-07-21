# Run a Behavior Qualification Suite

## Workflow

1. **Resolve an explicit catalog slice.** Select case ids, a family, critical-suite label, or manifest-route coverage set; record exclusions.
2. **Invoke `plan-run` once** to freeze the suite, provider/context partitions, attempt matrix, and resource bounds.
3. **Execute cases in isolation.** Use `execute-case` and `adjudicate-case` for each planned attempt without sharing provider conversations.
4. **Preserve dependency and infrastructure failures.** Continue independent cases when safe, but do not convert skipped cases to passes.
5. **Invoke `report-run`** for per-case aggregates and the suite coverage summary.
6. **Return outcome counts, flaky cases, stable failures, inconclusive cases, activation-unobserved cases, evidence root, and cleanup status.**

If the requested suite mixes admin, managed-agent, missing-dependency, and lifecycle contexts, use the native planning tool to batch only compatible fixture setup while preserving fresh conversation boundaries.

## Guardrails

- DO NOT let one case's response or oracle enter another case's prompt context.
- DO NOT call a partial provider matrix complete without listing unsupported or unexecuted cells.
