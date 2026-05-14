# V4 Reporting Template

Use this structure for generated files under `templates/reporting/`. Keep headings in this order. If a required value is unknown, write `UNRESOLVED - <reason>`.

```md
# <Report Name>

# Required Fields
| Field | Owner | Required When | Value |
| --- | --- | --- | --- |
| <field> | <agent> | <state or trigger> | <placeholder> |

# Source Constraints Applied
| ID | Verb | Rule | Report Projection |
| --- | --- | --- | --- |
| SC-001 | `<VERB>` | `<source rule>` | `<required report field or format>` |

# Evidence Fields
| Evidence | Source | Required Format |
| --- | --- | --- |
| <evidence> | <command, file, mailbox, or manual observation> | <format> |

# Output Format
<strict output schema, table, checklist, or prose contract>

# Unresolved Inputs
- `UNRESOLVED - <reason>`
```
