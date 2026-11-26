---
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

# Logical Mount Scope, Role Templates, and Mode-Aware Signer Selection

## Qualified `skills` and `mcp` Mounts

- **`skills` mount (`managed_web_skills`)**: requires an owner-enabled DSH Web agent running the qualified DSH `0.2.2-rc.3` build and native `standard` preset with `--prompt-mode as_is` and default native permission parameters:

  ```bash
  houmao-mgr project profile set --name "$PROFILE_NAME" --prompt-mode as_is \
    --tool-params '{"managed_web_skills":true}'
  ```

  Existing skill sources outside the mount do not become managed files, and `mounts` discovery returns only mounts the caller is authorized to read.
- **`mcp` mount (`managed_web_mcp` + `mcp_servers`)**: supported on the same qualified DSH Web build when the owner enables `managed_web_mcp` and pre-approves HTTP connectors in `mcp_servers` before launch. Draft files (for example `review.json`) reference an approved connector via `{"connector":"review-api"}` and optional `enabled`; endpoints and secrets remain owner-controlled outside the mount. Discover via `mounts --kind mcp`; publication requires a dedicated native host.

## Permissions, Built-In `agent-maintainer`, and `skill-*` Role Templates

| Operation | Required Permission on `files:<mount-id>` | Matching Role Templates (`access role-put --template ... --resource files:<mount-id>`) |
| --- | --- | --- |
| Discover mount, read published revisions/candidates, or reconcile an `operation_id` | `files.read` | `skill-reviewer`, `skill-editor`, `skill-publisher`, `skill-maintainer` |
| Open/renew exclusive lease (2 MiB decoded write cap), stage/edit/commit/discard private draft | `files.edit` (+ private `umask 077` `--lease-capability-file` when anonymous) | `skill-editor`, `skill-maintainer` |
| Publish a saved candidate (`push`) | `files.push` | `skill-publisher`, `skill-maintainer` |

Assigning `builtin:agent-maintainer` (or `agent-operator` / `agent-admin`) grants read, edit, and push across the target's common `skills` and `mcp` mounts, whereas `skill-reviewer`, `skill-editor`, `skill-publisher`, and `skill-maintainer` scope exact capabilities to one discovered `files:<mount-id>` resource (managed via `houmao-shared-routines->houmao-agent-access->policy()`).

## Target Coordinates and Mode-Aware (`open` vs `keyed`) Signer Selection

Check target `admin_mode` (`/v1/endpoint` or `gateway status`) before choosing at most one signer option on `agents single ... files` (remote callers supply `--agent-id` with trusted `--url`, `--context-id`, `--generation`, `--presence`, and optional `--ca-bundle`):

- **Managed self (`agents self files`)**: uses the attached gateway and current `managed-self` registration automatically.
- **Open-roster mode (`admin_mode: open`)**: pass `--unsigned` explicitly to use initialized open admission (anonymous draft leases return a private `lease_capability` that must be saved with `umask 077` for `--lease-capability-file` alongside the admitting open epoch).
- **Keyed mode (`admin_mode: keyed`)**: choose `--signer ABSOLUTE_PRIVATE_KEY` (explicit enrolled key), `--source-agent-id SOURCE_ID` (verified locally owned source agent's peer signer, even when stopped), or `--self-signer` (current managed self's peer signer); pass `--unsigned` in `keyed` mode only when relying on a target `default-group` that explicitly grants `agent-maintainer` or higher.

A missing, stale, or `admin_mode: unavailable` listener blocks file operations fail-closed.
