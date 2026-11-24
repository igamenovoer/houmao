---
name: houmao-agent-files
description: Use when an authorized caller needs to inspect, edit, commit, publish, or reconcile versioned logical files on a selected Houmao agent.
license: MIT
metadata:
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

# Houmao Agent Files

## Workflow

1. Answer explicit help from **Help** before selecting a target or contacting a gateway.
2. Apply the **Actor Frame Gate** and select an operation from **Subcommands**.
3. Load the selected command page. Carry forward only verified target, signer, mount, draft, base, candidate, and operation evidence that the page requires.
4. Stop at the requested boundary. Report the logical mount and what the response confirms about the draft, candidate, publication, native activation, or readiness.

If a request spans supported operations, use the native planning tool to plan those steps while preserving the selected target and permission boundaries.

## Actor Frame Gate

Accept only the immutable admin or verified managed-agent frame established by `houmao-shared-routines`. Require an explicit target for a peer edit. Verify the target gateway and use the chosen caller's current mount authority.

- **Owner-local caller.** Select the target by ID or name in its verified execution-owner context. Use an appropriate enrolled key or the initialized open-roster path.
- **Managed peer.** Preserve verified self as the source. Select the target by exact ID and trusted endpoint coordinates. Use the configured source peer signer when signing as this agent.
- **Operator using an independent source.** Select either a locally owned configured source or an explicitly authorized private signing key. The source gateway and tmux topology do not determine access to the target.

For enrollment and exact resource grants, use `houmao-shared-routines->houmao-agent-access`. Ordinary native home and skill/MCP freshness questions belong to `houmao-shared-routines->houmao-agent-instance->native-resources()`.

## Subcommands

### Procedural Subcommands

| Subcommand | Operation | Detail |
| --- | --- | --- |
| `discover()` | Select the verified target and find the exact mount and published base. | [Discover](commands/discover.md) |
| `inspect()` | Read published files, an exact revision, an active draft, or a saved candidate. | [Inspect](commands/inspect.md) |
| `edit-draft()` | Open or renew a private lease, stage and review changes, then save or discard them. | [Edit Draft](commands/edit-draft.md) |
| `publish()` | Request publication of one saved candidate against its recorded base. | [Publish](commands/publish.md) |
| `reconcile()` | Read a retained attempt by its original operation ID. | [Reconcile](commands/reconcile.md) |

### Misc Subcommands

| Subcommand | Operation |
| --- | --- |
| `help()` | Explain the workflow and prerequisites without connecting or changing state. |

## Help

Explain that the current qualified provider is the owner-enabled DSH Web `skills` mount. Outline discovery, read-only inspection, private draft editing, candidate publication, and receipt reconciliation. Example starting points are `$houmao-agent-entrypoint agent-files discover for TARGET` and `$houmao-admin-entrypoint agent-files reconcile for TARGET`. Answer from this section without collecting targets or running commands.

## Guardrails

- DO NOT read or edit the target agent's filesystem directly as a fallback for an unavailable logical mount.
- DO NOT infer a mount ID, base, grant, or gateway identity from display names or paths.
- DO NOT expose signing material or an anonymous draft capability in logs, chat, or shared files.
- DO NOT treat a saved candidate as published or a publication as native readiness.
- DO NOT replay a push with an uncertain result or trigger a refresh to force settlement.
