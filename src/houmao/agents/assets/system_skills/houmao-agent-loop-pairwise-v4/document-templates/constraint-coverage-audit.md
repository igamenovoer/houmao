# V4 Constraint Coverage Audit Template

Fill this template as `<plan-output-dir>/constraint-coverage-audit.md` for bundle plans, or inline under `# Constraint Coverage Audit` for single-file plans. Keep headings in this order. If a required value is unknown, write `UNRESOLVED - <reason>`.

```md
# Constraint Coverage Audit

# Source Inputs
| Source | Kind | Notes |
| --- | --- | --- |
| <path or instruction> | <task note | user-provided document | commons | rulebook | manual tuning | user instruction> | <why it matters> |

# Coverage Table
| ID | Source | Verb | Scope | Rule | Central Projection | Runtime Projection | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SC-001 | <source> | `<VERB>` | <central | role | reporting | bookkeeping | routing> | <source rule> | <plan.md section> | <packet, agent note, report, bookkeeping, script, or support file> | <covered | unresolved | excluded> |

# Unresolved Or Excluded Items
- `UNRESOLVED - <reason>`

# Final Audit Decision
<covered, blocked by unresolved inputs, or intentionally partial with reasons>
```
