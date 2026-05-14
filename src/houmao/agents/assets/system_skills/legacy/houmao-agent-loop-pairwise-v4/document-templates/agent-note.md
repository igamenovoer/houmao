# V4 Agent Note Template

Fill this template for each generated `agents/<participant>.md`. Keep headings in this order. If a required value is unknown, write `UNRESOLVED - <reason>`.

```md
# Agent Note: <agent-name>

# Role
- specialist or team role: <role>
- immediate driver: <agent or operator>
- result returns to: <agent or operator>
- delegation authority: <none or named children>

# Source Constraints Carried Forward
| ID | Verb | Rule | Local Action |
| --- | --- | --- | --- |
| SC-001 | `<VERB>` | `<source rule>` | `<how this agent must apply it>` |

# Hard Gates
- `CHECK`: <precondition that must pass before work continues>
- `NEVER`: <forbidden local action>
- `ALWAYS`: <required local action or invariant>

# SOP
- `READ`: <source, memo, packet, or file to read before acting>
- `ANALYZE`: <local analysis obligation>
- `DECIDE`: <decision point and escalation rule>
- `RUN`: <allowed command or validation>
- `OUTPUT`: <required output shape>
- `DISPATCH`: <child request or result-return behavior>

# Reporting And Evidence Duties
- evidence to collect: <paths, commands, screenshots, reports, or messages>
- report destination: <mailbox, report template, bookkeeping path, or immediate driver>
- cadence: <on completion, per round, after failure, or explicit trigger>

# Related Skills
- <skill name>: <when to use it or why it is not needed>

# Unresolved Role Inputs
- `UNRESOLVED - <reason>`
```
