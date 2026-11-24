---
name: houmao-agent-access
description: Use when a Houmao gateway needs retained access policy, administrator key enrollment, peer signer setup, scoped grants, or an authenticated request to a selected agent.
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
5. Report the target, operation, policy or gateway outcome, and any unresolved evidence. Keep private signing material out of the response.

If the request does not fit these steps, use the native planning tool to plan and execute the smallest supported sequence within the verified actor frame.

## Actor Frame Gate

Accept only the immutable admin or verified managed-agent frame established by `houmao-shared-routines`. The public skill route selects a workflow. Houmao and the selected gateway verify the actual owner or caller.

- **Execution owner.** Use the admin frame and the selected agent's verified local execution context for retained target policy or local source signer configuration. These operations work with the gateway detached.
- **Live roster administrator.** Use the admin frame and the appropriate signing proof with an explicitly selected live target. First-key enrollment uses proof of possession of the proposed key.
- **Managed peer.** Preserve verified self as the source. Export its configured public identity or request an authorized operation on an explicit target. For enrollment or a grant, identify the exact public identity and requested resource and action for the target owner.
- **Operator using a local source agent.** Select a verified, locally owned source explicitly for a signed request. The source can be stopped.

For a provider login or API credential, explain the scope and direct the authorized operator to `houmao-shared-routines->houmao-credential-mgr`. For versioned logical files, use `houmao-shared-routines->houmao-agent-files`.

## Subcommands

| Subcommand | Operation | Detail |
| --- | --- | --- |
| `help()` | Explain the owner, live administrator, and peer workflows. | **Help** |
| `provision()` | Initialize or recover retained policy for the selected execution owner. | [Provision](commands/provision.md) |
| `policy()` | Manage principals, enrolled keys, scoped grants, and roles. | [Policy](commands/policy.md) |
| `admin-roster()` | Add or remove a live gateway administrator qualification. | [Admin Roster](commands/admin-roster.md) |
| `peer-identity()` | Configure an owned source signer or export the managed source's public identity. | [Peer Identity](commands/peer-identity.md) |
| `request()` | Send a supported signed JSON request to a verified target gateway. | [Request](commands/request.md) |

## Help

Explain the supported operations, authority requirements, and difference between initializing retained policy and reaching a live gateway. Example starting points are `$houmao-admin-entrypoint agent-access policy` and `$houmao-agent-entrypoint agent-access peer-identity`. Return help without looking up a target, accessing a key, calling a gateway, or changing policy.

## Guardrails

- DO NOT infer execution ownership from a user label, a tmux session, an admin frame, or live gateway administrator access.
- DO NOT change owner-local policy or configure a local signer from a managed-agent frame.
- DO NOT send private keys, proof contents, or owner-private files through responses or shared messages.
- DO NOT replace missing gateway coordinates or rejected proof with a guessed endpoint, caller, or transport.
