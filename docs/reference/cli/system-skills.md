# `system-skills`

This page documents `houmao-mgr system-skills` command behavior. The command group installs, inspects, upgrades, and removes complete Houmao actor packs in external or project-scoped tool homes. Managed launch and join use the same pack lifecycle internally.

```text
houmao-mgr system-skills list
houmao-mgr system-skills install --tool <target> [--home <path>] [--pack admin|agent]... [--symlink]
houmao-mgr system-skills status --tool <target> [--home <path>]
houmao-mgr system-skills upgrade --tool <target> [--home <path>] [--pack admin|agent]... [--symlink]
houmao-mgr system-skills uninstall --tool <target> [--home <path>] [--pack admin|agent]...
```

Use the root `--print-json` flag before `system-skills` for structured output:

```bash
houmao-mgr --print-json system-skills list
houmao-mgr --print-json system-skills status --tool codex --home ~/.codex
```

There is no `system-skills help` subcommand. Public skill help comes from `$houmao-admin-welcome help`, `$houmao-admin-entrypoint help`, or `$houmao-agent-entrypoint help`.

## Packs and Public Paths

| Pack | Audience | Public Paths | Default Lane |
|---|---|---|---|
| `admin` | Human operator | `houmao-admin-welcome`, `houmao-admin-entrypoint` | Explicit CLI install |
| `agent` | Managed Houmao agent | `houmao-agent-entrypoint` | Managed launch, rebuild, relaunch, and join |

The admin pack is atomic: both public paths install, refresh, and uninstall together. Protected `houmao-shared-routines` content is composed beneath executable entrypoints. Protected logical ids are inspection records and route arguments, never install selectors or top-level projections.

`houmao-auto-system-prompt` is a separate managed auto skill. It does not belong to either pack and does not appear in pack receipts.

## Supported Targets and Effective Homes

Supported target names are `claude`, `codex`, `copilot`, `kimi`, and `universal`. Gemini is not a supported system-skill target.

| Target | Environment Redirect | Project Default | Public Root |
|---|---|---|---|
| `claude` | `CLAUDE_CONFIG_DIR` | `<cwd>/.claude` | `<home>/skills` |
| `codex` | `CODEX_HOME` | `<cwd>/.codex` | `<home>/skills` |
| `copilot` | `COPILOT_HOME` | `<cwd>/.github` | `<home>/skills` |
| `kimi` | `KIMI_CODE_HOME` | `<cwd>/.kimi-code` | `<home>/skills` |
| `universal` | None | `~/.agents` | `<home>/skills` |

`--home` overrides environment and project defaults for one target. A comma-separated multi-target value such as `--tool claude,codex,kimi` must omit `--home` so each target resolves independently. `kimi` means Kimi Code CLI.

Copilot discovery under `.github/skills` does not by itself provide access to local Houmao runtime resources. Commands still require an environment where `houmao-mgr`, project state, tmux sessions, gateways, and mailboxes are reachable.

Kimi discovers projected skills when a later launch uses the same `KIMI_CODE_HOME`, passes the path through `--skills-dir`, or lists it in `extra_skill_dirs`. Managed Kimi homes add their projected root to `config.toml` `extra_skill_dirs`.

## `list`

`list` reads the versioned manifest and reports:

- pack id, audience, description, and default lanes;
- each public skill's name, role, and public commands;
- audience-eligible protected logical ids;
- protected route names, dependencies, commands, and actor-qualified invocation designators;
- the separate auto-skill name.

Plain output summarizes the two packs and protected counts. JSON output contains `schema_version`, `packs`, `defaults`, `protected_routines`, and `auto_skill_separate`.

```bash
houmao-mgr system-skills list
houmao-mgr --print-json system-skills list
```

## `install`

Omitting `--pack` selects `admin` for this explicit external-home command. Repeat `--pack` to install both complete packs:

```bash
houmao-mgr system-skills install --tool codex
houmao-mgr system-skills install --tool codex --pack admin
houmao-mgr system-skills install --tool codex --pack agent
houmao-mgr system-skills install --tool codex --pack admin --pack agent
houmao-mgr system-skills install --tool universal --home ~/.agents --pack admin
```

Copy projection is the default. `--symlink` links each public path to a complete receipt-owned composition under the hidden materialization root; it never links to an uncomposed public source directory:

```bash
houmao-mgr system-skills install --tool codex --home ~/.codex --pack admin --symlink
```

Before mutation, installation stages and recursively validates every selected composition. It rejects untracked collisions at selected public paths, preserves unrelated skills, backs up replaceable receipt-owned state, commits all selected public members, and writes the receipt last. Any failure rolls the transaction back.

Structured install output reports `tool`, `home_path`, `selected_packs`, `public_skills`, `projected_relative_dirs`, `receipt_path`, `projection_mode`, `protected_logical_ids_by_public`, and any removed or safely migrated paths.

Individual `--skill` and set-based `--set` or `--skill-set` selectors are obsolete. When encountered, the CLI directs the caller to repeat `--pack admin|agent`. Passing `houmao-shared-routines` or a protected logical id to `--pack` fails because protected routines cannot be installed independently.

## Ownership Receipt

Each target keeps one tool-scoped receipt:

```text
<home>/.houmao/system-skills/<tool>/receipt.json
```

Symlink mode also owns complete materializations beneath:

```text
<home>/.houmao/system-skills/<tool>/materialized/
```

The versioned receipt records package and manifest versions, tool and home, selected packs, public roles and paths, projection mode, content digests, mounted protected logical ids, materialization paths, update time, and safely removed legacy paths.

Receipt writes are atomic. A missing receipt is reported read only as `absent`. Invalid JSON or invalid current-version data is `corrupt`. A future schema version is `unsupported`; lifecycle mutation refuses to guess ownership until the operator resolves it.

## `status`

Status never repairs or mutates the target. It reports receipt state, every manifest pack's integrity, and legacy flat-path evidence:

```bash
houmao-mgr system-skills status --tool codex
houmao-mgr system-skills status --tool codex --home ~/.codex
houmao-mgr --print-json system-skills status --tool kimi
```

Pack integrity classes are:

| Status | Meaning |
|---|---|
| `absent` | The receipt does not own the pack. |
| `complete` | Every receipt-owned public role and protected composition matches its digest and projection shape. |
| `incomplete` | One or more receipt-owned public paths or materializations are missing. |
| `drifted` | Receipt-owned content exists but its digest differs, or its recorded manifest schema predates the current composition contract. |
| `conflicting` | A public path has the wrong type, target, or ownership shape. |

Legacy flat-path classifications are:

| Classification | Meaning |
|---|---|
| `package-linked` | A symlink targets the old packaged location recorded by the v1 catalog. |
| `digest-matched` | A complete copied tree matches a known v1 digest. |
| `modified` | A known legacy path contains different content or points elsewhere. |
| `unknown` | An unrecognized `houmao-*` path exists outside current public paths. |

Legacy aggregate state is `absent`, `complete`, `partial`, or `conflicting`. This evidence is deliberately separate from current receipt ownership.

## `upgrade`

`upgrade` refreshes selected complete packs through the same transaction path and conservatively migrates legacy flat paths:

```bash
houmao-mgr system-skills upgrade --tool codex --home ~/.codex --pack admin
houmao-mgr system-skills upgrade --tool codex --home ~/.codex --pack agent --symlink
```

Omitting `--pack` selects the explicit CLI default `admin`. Upgrade also replaces receipt-owned packs whose recorded manifest schema predates the current parent-scoped `SKILL-MAIN.md` composition. It removes only `package-linked` and `digest-matched` legacy paths, preserves `modified` and `unknown` paths, lists them in `preserved_legacy_paths`, and leaves unrelated content untouched.

Use this sequence for a breaking flat-to-pack migration:

```bash
houmao-mgr system-skills status --tool codex --home ~/.codex
houmao-mgr system-skills upgrade --tool codex --home ~/.codex --pack admin
houmao-mgr system-skills status --tool codex --home ~/.codex
```

If status reports a modified or unknown legacy conflict, compare and move or remove that path manually after preserving any customization. Rerun status and upgrade afterward. Do not treat a partial v1 tree as current ownership.

## `uninstall`

Uninstall removes only selected receipt-owned packs and their receipt-owned materializations. Omission selects all packs currently owned by the receipt:

```bash
houmao-mgr system-skills uninstall --tool codex --pack admin
houmao-mgr system-skills uninstall --tool codex --pack agent
houmao-mgr system-skills uninstall --tool codex
```

When one selected pack has an ownership-shape conflict, uninstall preserves its paths and reports `preserved_conflicting_paths`. Other independently removable selected packs may still be removed. Unrelated user skills and unowned legacy paths remain untouched. The receipt disappears when no owned packs remain.

Structured output reports requested, removed, and absent packs; removed public paths; preserved conflicts; and the receipt path.

## Managed-Home Policy

Managed launch, rebuild, relaunch, and join use `agent` when policy is omitted. Source policy modes are `default`, `extend`, `replace`, and `none`; profile policy modes are `inherit`, `extend`, `replace`, and `none`.

```yaml
launch:
  system_skills:
    mode: extend
    packs:
      - admin
```

`extend` on a source starts from the managed `agent` default. `replace` selects exactly the listed packs. `none` selects no packs. On a reused home, exact sync removes only receipt-owned packs no longer selected and preserves unrelated user skills.

Stored `sets` and `skills` fields are rejected with a migration diagnostic. Public entrypoints and complete packs are the only selection units.

## Public Invocations and Protected Route Traces

The CLI can report protected metadata, but users invoke a public entrypoint. The following table maps all eighteen protected logical ids. Designators in the third column are internal route traces.

| Logical ID | Eligible Public Entrypoint | Internal Route Trace | Major Command Family |
|---|---|---|---|
| `houmao-project-mgr` | Admin | `houmao-admin-entrypoint->houmao-shared-routines->project-mgr` | `project ...` |
| `houmao-credential-mgr` | Admin | `houmao-admin-entrypoint->houmao-shared-routines->credential-mgr` | `project credentials ...`, native credential internals |
| `houmao-agent-definition` | Admin | `houmao-admin-entrypoint->houmao-shared-routines->agent-definition` | specialist, profile, recipe, role, launch-dossier commands |
| `houmao-operator-messaging` | Admin | `houmao-admin-entrypoint->houmao-shared-routines->operator-messaging` | explicit-target prompt and mail dispatch |
| `houmao-process-emails-via-gateway` | Agent | `houmao-agent-entrypoint->houmao-shared-routines->process-emails-via-gateway` | prompt-provided gateway `/v1/mail/*` round |
| `houmao-agent-email-comms` | Admin, Agent | `<entrypoint>->houmao-shared-routines->agent-email-comms` | scoped `mail ...` and gateway mail API |
| `houmao-adv-usage-pattern` | Admin, Agent | `<entrypoint>->houmao-shared-routines->adv-usage-pattern` | mailbox, notifier, reminder, and wakeup compositions |
| `houmao-utils-workspace-mgr` | Admin, Agent | `<entrypoint>->houmao-shared-routines->utils-workspace-mgr` | workspace preparation and project readiness |
| `houmao-ext-graphing` | Admin, Agent | `<entrypoint>->houmao-shared-routines->ext-graphing` | `ag-ui impl ...` graphing payloads |
| `houmao-mailbox-mgr` | Admin, Agent | `<entrypoint>->houmao-shared-routines->mailbox-mgr` | mailbox root, registration, and binding commands |
| `houmao-memory-mgr` | Admin, Agent | `<entrypoint>->houmao-shared-routines->memory-mgr` | scoped `memory ...` |
| `houmao-agent-loop-pro` | Admin, Agent | `<entrypoint>->houmao-shared-routines->agent-loop-pro` | schema-rich generated loop authoring and controls |
| `houmao-agent-loop-lite` | Admin, Agent | `<entrypoint>->houmao-shared-routines->agent-loop-lite` | Markdown/direct-SQL generated loop authoring and controls |
| `houmao-agent-instance` | Admin, Agent | `<entrypoint>->houmao-shared-routines->agent-instance` | launch, join, list, stop, relaunch, cleanup |
| `houmao-agent-inspect` | Admin, Agent | `<entrypoint>->houmao-shared-routines->agent-inspect` | identity, screen, mailbox, artifacts, logs |
| `houmao-agent-messaging` | Admin, Agent | `<entrypoint>->houmao-shared-routines->agent-messaging` | prompt, interrupt, queue, send keys, mail, reset context |
| `houmao-agent-gateway` | Admin, Agent | `<entrypoint>->houmao-shared-routines->agent-gateway` | gateway lifecycle, status, reminders, notifier, watch |
| `houmao-interop-ag-ui` | Admin, Agent | `<entrypoint>->houmao-shared-routines->interop-ag-ui` | AG-UI validate, frame, render, publish |

For a shared route, replace `<entrypoint>` with `houmao-admin-entrypoint` or `houmao-agent-entrypoint` according to the caller. Admin routes require explicit targets. Agent routes verify identity and default self-scoped operations to verified self.

Copyable examples:

```text
$houmao-admin-entrypoint credential-mgr list
$houmao-admin-entrypoint agent-definition profiles
$houmao-admin-entrypoint agent-inspect status for reviewer-1
$houmao-agent-entrypoint agent-email-comms status
$houmao-agent-entrypoint process-emails-via-gateway http://127.0.0.1:43123
```

## Breaking Selector and Name Migration

| Removed Surface | Replacement |
|---|---|
| `--skill <name>` | `--pack admin` or `--pack agent` |
| `--set` / `--skill-set core|extensions|all` | Repeat complete `--pack` selectors |
| Stored `skills:` / `sets:` | Stored `packs:` |
| `$houmao-touring ...` | `$houmao-admin-welcome ...` |
| `$houmao-specialist-mgr ...` | `$houmao-admin-entrypoint agent-definition specialists|profiles ...` |
| Any low-level `$houmao-<routine> ...` | `$houmao-admin-entrypoint <route> ...` or `$houmao-agent-entrypoint <route> ...` according to actor eligibility |

Old names remain only in migration evidence and the read-only v1 digest inventory. They are not compatibility wrappers.

## Errors and Safety Notes

- Unknown packs fail before multi-target mutation.
- Duplicate tool names and empty comma-separated tool entries fail validation.
- `--home` with multiple tools fails because one path cannot represent several target-native homes.
- Untracked selected-path collisions fail preflight and remain unchanged.
- Corrupt or future-version receipts block lifecycle mutation but remain inspectable through status.
- Modified legacy content is preserved during upgrade.
- Protected ids and `houmao-auto-system-prompt` cannot be selected as packs.

## See Also

- [System Skills Overview](../../getting-started/system-skills-overview.md): actor model, guided paths, and route behavior.
- [Easy Specialists](../../getting-started/easy-specialists.md): persisted source pack policy.
- [Launch Profiles](../../getting-started/launch-profiles.md): source/profile policy precedence and reuse.
- [Mailbox Quick Start](../mailbox/quickstart.md): managed mailbox setup and agent-entrypoint routing.
