---
name: houmao-agent-access
description: Use when a Houmao gateway needs retained access policy, `default-group` or role-template setup, administrator key enrollment, `self-key` rotation, peer signer setup, scoped grants, or a signed request to a selected agent.
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

# Houmao Agent Access

## Workflow

1. Answer explicit help from **Help** before target lookup or command execution.
2. Apply the **Actor Frame Gate** and select one operation from **Subcommands**.
3. Resolve the intended agent and the caller's authority. Use [Access Scope](references/access-scope.md) to identify the required owner context or trusted endpoint details.
4. Load the selected command page. Run the supported scoped manager command only after all target, operation, and proof inputs are present.
5. Report the target, operation, policy or gateway outcome (including any immediate-admission stderr guidance), and any unresolved evidence. Keep private signing material out of the response.

If the request does not fit these steps, use the native planning tool to plan and execute the smallest supported sequence within the verified actor frame.

## Actor Frame Gate

Accept only the immutable admin or verified managed-agent frame established by `houmao-shared-routines`. The public skill route selects a workflow; Houmao and the selected gateway verify the actual owner or caller.

- **Execution owner**: use the admin frame and the selected agent's verified local execution context for retained target policy, `default-group` (`--retained` or `--passive-url`), `self-key {rotate|revoke}`, or local source signer configuration (works with the gateway detached).
- **Live roster administrator**: use the admin frame and appropriate signing proof with an explicitly selected live target (first-key enrollment uses proof of possession of the proposed key; rotate by qualifying the replacement key before removing the sole old admin key).
- **Managed peer**: preserve verified self as the source; export its configured public identity or invoke `houmao-shared-routines->houmao-agent-access->request()` against an explicit target.
- **Operator using a local source agent**: select a verified, locally owned source explicitly (`--source-agent-id`) for a signed request even if the source is stopped.

For provider API/OAuth credentials, route to `houmao-shared-routines->houmao-credential-mgr`. For versioned `skills` and `mcp` mounts, route to `houmao-shared-routines->houmao-agent-files`.

## Subcommands

| Subcommand | Operation | Detail |
| --- | --- | --- |
| `help` | Explain owner, live administrator, `default-group`, `self-key`, and peer workflows. | **Help** |
| `provision` | Initialize or recover retained policy for the selected execution owner. | [Provision](commands/provision.md) |
| `policy` | Manage principals, keys, `self-key`, `default-group`, built-in groups, role templates, and grants. | [Policy](commands/policy.md) |
| `admin-roster` | Add or remove a live gateway administrator qualification (`open` vs `keyed`). | [Admin Roster](commands/admin-roster.md) |
| `peer-identity` | Configure an owned source signer or export the managed source's public identity. | [Peer Identity](commands/peer-identity.md) |
| `request` | Send a supported signed JSON request to a verified target gateway. | [Request](commands/request.md) |

## Help

Explain the supported operations, authority separation, `open` (empty admin roster) vs `keyed` admission, the six built-in groups (`agent-observer` through `agent-admin` plus `managed-self`), role templates, and `self-key {rotate|revoke}`. Example starting points are `$houmao-admin-entrypoint agent-access policy` and `$houmao-agent-entrypoint agent-access peer-identity`. Answer read-only without probing targets, reading keys, or mutating policy.

## Guardrails

- DO NOT infer execution ownership from a user label, a tmux session, an admin frame, or live gateway administrator access.
- DO NOT change owner-local policy or configure a local signer from a managed-agent frame, or revoke the sole admin key before enrolling its replacement when remaining in keyed mode.
- DO NOT send private keys, proof contents, or owner-private files through responses or shared messages.
- DO NOT replace missing gateway coordinates or rejected proof with a guessed endpoint, caller, or transport.
