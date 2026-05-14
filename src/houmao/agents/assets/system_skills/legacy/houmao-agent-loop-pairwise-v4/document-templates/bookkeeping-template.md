# V4 Bookkeeping Template

Use this structure for generated files under `templates/bookkeeping/`. Keep headings in this order. If a required value is unknown, write `UNRESOLVED - <reason>`.

````md
# <Bookkeeping Name>

# Record Schema
```yaml
record_id: <stable id>
owner: <agent>
status: <pending | active | blocked | complete>
source_constraints:
  - <SC-001>
evidence:
  - path: <path or none>
    summary: <summary>
updated_at: <manual timestamp or trigger>
```

# Source Constraints Applied
| ID | Verb | Rule | Bookkeeping Projection |
| --- | --- | --- | --- |
| SC-001 | `<VERB>` | `<source rule>` | `<state field, owner rule, evidence field, or update trigger>` |

# Update Rules
- `UPDATE`: <when this record is updated>
- `CHECK`: <what must be verified before changing status>
- `OUTPUT`: <where filled records are written during execution>

# Ownership
- authoring owner: <who owns template changes>
- runtime owner: <who owns filled mutable records>
- mutable output path: <declared bookkeeping path outside reusable templates>

# Unresolved Inputs
- `UNRESOLVED - <reason>`
````
