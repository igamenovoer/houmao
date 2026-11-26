---
name: houmao-agent-files
description: Use when an authorized caller needs to inspect, edit, commit, publish (`--when-idle`), or reconcile versioned `skills` and `mcp` logical files on a selected Houmao agent.
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
3. Load the selected command page (and [Mount Scope](references/mount-scope.md) / [Push Receipts](references/receipts.md) as needed). Carry forward only verified target, signer (`open` vs `keyed`), mount, draft, base, candidate, and operation evidence that the page requires.
4. Stop at the requested boundary. Report the logical mount and what the response confirms about the draft, candidate, publication, native activation, or readiness.

If a request spans supported operations, use the native planning tool to plan those steps while preserving the selected target and permission boundaries.

## Actor Frame Gate

Accept only the immutable admin or verified managed-agent frame established by `houmao-shared-routines`. Require an explicit target for a peer edit. Verify the target gateway and use the chosen caller's current mount authority (`builtin:agent-maintainer` or exact `files:<mount-id>` grants/role templates).

- **Owner-local caller**: select the target by ID or name in its verified execution-owner context; use an enrolled `--signer` key in `keyed` mode or `--unsigned` on an initialized `open` roster.
- **Managed self**: inside your own runtime, use `agents self files` with the current `managed-self` registration (supporting `push --when-idle` while your turn is active).
- **Managed peer**: preserve verified self as the source, select the target by exact ID and trusted endpoint coordinates, and pass `--self-signer` (or `--unsigned` when open/default policy permits).
- **Operator using an independent source**: select either a locally owned configured source (`--source-agent-id`, even if stopped) or an explicitly authorized `--signer` private key.

For enrollment, `agent-maintainer`, and `skill-*` role templates (`skill-reviewer`, `skill-editor`, `skill-publisher`, `skill-maintainer`), use `houmao-shared-routines->houmao-agent-access`. Ordinary native home and skill/MCP freshness questions belong to `houmao-shared-routines->houmao-agent-instance->native-resources()`.

## Subcommands

### Procedural Subcommands

| Subcommand | Operation | Detail |
| --- | --- | --- |
| `discover` | Select the verified target and find the exact `skills` or `mcp` mount and published base. | [Discover](commands/discover.md) |
| `inspect` | Read published files, an exact revision, an active draft, or a saved candidate. | [Inspect](commands/inspect.md) |
| `edit-draft` | Open or renew an exclusive private lease (`umask 077` capability, 2 MiB limit), stage/review changes, then commit or discard. | [Edit Draft](commands/edit-draft.md) |
| `publish` | Publish one saved candidate against `--expected-base` with `--operation-id` (or self `push --when-idle`). | [Publish](commands/publish.md) |
| `reconcile` | Read a retained publication attempt by its original `--operation-id`. | [Reconcile](commands/reconcile.md) |

### Helper Subcommands

No helper subcommands are currently exposed.

### Misc Subcommands

| Subcommand | Operation |
| --- | --- |
| `help` | Explain the workflow, `skills`/`mcp` mounts, role templates, and prerequisites without connecting or changing state. |

## Help

Explain that qualified DSH Web runtimes expose owner-enabled `skills` (`managed_web_skills`) and `mcp` (`managed_web_mcp` with `mcp_servers`) mounts, outline `discover -> inspect -> edit-draft -> publish -> reconcile`, and note `agent-maintainer` / `skill-*` role templates plus `open` vs `keyed` signer selection. Example starting points are `$houmao-agent-entrypoint agent-files discover for TARGET` and `$houmao-admin-entrypoint agent-files reconcile for TARGET`. Answer read-only without running commands.

## Guardrails

- DO NOT read or edit the target agent's filesystem directly as a fallback for an unavailable logical mount.
- DO NOT infer a mount ID, base, grant, or gateway identity from display names or paths.
- DO NOT expose signing material or an anonymous `lease_capability` (`umask 077` `--lease-capability-file`) in logs, chat, or shared files.
- DO NOT treat a saved candidate as published or a publication receipt as native readiness.
- DO NOT replay a push with an uncertain result or trigger `refresh` to force settlement; use `reconcile` with the original `--operation-id`.
