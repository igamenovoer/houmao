---
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Shared Routine Help

## Workflow

1. **Keep the request read-only** and avoid actor verification, target discovery, child loading, and command execution.
2. **Identify the requested scope** as collection-wide help, one child, the specialist compatibility alias, or a loop sibling.
3. **Describe direct posture**: default admin, optional leading `as-agent` with fresh verification, or an inherited immutable frame.
4. **List relevant routes and invocation forms** without executing a default child operation.
5. **Return one concrete next invocation** when the caller asks how to proceed.

If the help request does not map cleanly to these steps, use the native planning tool to build a bounded read-only response from the collection route table, actor matrix, child help contracts, and caller question, then answer without execution.

Collection-wide help lists sixteen parent-scoped children, `specialist-mgr` as an admin alias, and pro and lite as top-level siblings. Child-scoped help describes only that child's preserved operations and boundaries. Use `houmao-shared-routines->houmao-agent-inspect->discover()` style for child commands and `$houmao-shared-routines [as-agent] <route> <operation>` for visible direct invocation.
