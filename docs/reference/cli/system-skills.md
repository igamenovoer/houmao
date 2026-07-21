# `system-skills`

`houmao-mgr system-skills` installs, inspects, upgrades, and removes complete Houmao actor packs in external or project-scoped tool homes. Managed launch and join use the same static pack lifecycle internally.

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

There is no `system-skills help` subcommand. Skill-level help comes from `$houmao-admin-welcome help`, `$houmao-admin-entrypoint help`, `$houmao-agent-entrypoint help`, `$houmao-shared-routines help`, or either top-level loop's `help` operation.

## V4 Static Collection and Pack Membership

The `houmao-system-skills.v4` manifest records six standalone source directories. Each one has a role, activation posture, pack owners, commands, aliases, dependencies, and a complete source path. It also records sixteen parent-scoped children owned by shared routines, including actor eligibility, route name, dependencies, commands, and aliases.

| Pack | Audience | Static Top-Level Members | Default Lane |
|---|---|---|---|
| `admin` | Human operator | `houmao-admin-welcome`, `houmao-admin-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, `houmao-agent-loop-lite` | Explicit CLI install |
| `agent` | Managed Houmao agent | `houmao-agent-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, `houmao-agent-loop-lite` | Managed launch, rebuild, relaunch, and join |

`houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite` belong to both packs. A combined install has six unique destinations and records both owners on those three shared records.

The sixteen shared children use `SKILL-MAIN.md` below `houmao-shared-routines/subskills/`. They are route targets, not top-level install members. `houmao-auto-system-prompt` is a separate managed auto skill and never appears in the v4 manifest, static pack receipt, or public-root inventory.

## Standard External Installation

The public source at `src/houmao/agents/assets/system_skills/public/` is a valid static Agent Skills collection. A standard Skills CLI can list or install it without running Houmao's manager:

```bash
npx skills add ./src/houmao/agents/assets/system_skills/public --list
npx skills add ./src/houmao/agents/assets/system_skills/public --agent codex --skill '*' --yes
```

Select all five admin siblings explicitly:

```bash
npx skills add ./src/houmao/agents/assets/system_skills/public --agent codex --skill houmao-admin-welcome --skill houmao-admin-entrypoint --skill houmao-shared-routines --skill houmao-agent-loop-pro --skill houmao-agent-loop-lite --yes
```

Select all four agent siblings explicitly:

```bash
npx skills add ./src/houmao/agents/assets/system_skills/public --agent codex --skill houmao-agent-entrypoint --skill houmao-shared-routines --skill houmao-agent-loop-pro --skill houmao-agent-loop-lite --yes
```

Skills CLI and copy-paste installation treat each directory independently. They do not resolve Houmao dependencies, create shared owner sets, or write a Houmao receipt. Selecting an entrypoint alone therefore produces an incomplete actor surface. Use `houmao-mgr system-skills` when you want automatic pack closure and receipt-aware lifecycle management.

## Supported Targets and Effective Homes

Supported target names are `claude`, `codex`, `copilot`, `kimi`, and `universal`. Gemini is not a supported manager target.

| Target | Environment Redirect | Project Default | Skill Root |
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

`list` reads the v4 manifest and reports:

- each pack's id, audience, description, complete standalone membership, and default lanes;
- each of the six standalone skills with role, activation posture, pack owners, commands, aliases, and dependencies;
- each of the sixteen shared children with route, audiences, dependencies, commands, aliases, and parent-qualified invocation;
- the three overlapping standalone members;
- the separate auto-skill name.

```bash
houmao-mgr system-skills list
houmao-mgr --print-json system-skills list
```

JSON output contains `schema_version`, `packs`, `standalone_skills`, `shared_routines`, `overlapping_standalone_skills`, `defaults`, and `auto_skill_separate`.

## `install`

Omitting `--pack` selects `admin` for this explicit external-home command. Repeat `--pack` to install both complete packs:

```bash
houmao-mgr system-skills install --tool codex
houmao-mgr system-skills install --tool codex --pack admin
houmao-mgr system-skills install --tool codex --pack agent
houmao-mgr system-skills install --tool codex --pack admin --pack agent
houmao-mgr system-skills install --tool universal --home ~/.agents --pack admin
```

Copy projection is the default and recursively preserves the complete packaged directory bytes. `--symlink` links every top-level destination directly to its complete packaged source directory. Neither mode renders actor names, filters shared children, or creates a hidden composition tree.

```bash
houmao-mgr system-skills install --tool codex --home ~/.codex --pack admin --symlink
```

Before mutation, installation resolves a deduplicated static union, checks every destination for unowned collisions, stages complete directories, validates the union, and backs up replaceable receipt-owned state. It commits all destinations and writes the receipt last. A failure restores the prior paths and receipt. Unrelated user skills remain untouched.

Structured install output reports `tool`, `home_path`, `selected_packs`, `standalone_skills`, `projected_relative_dirs`, `receipt_path`, `projection_mode`, `owning_pack_ids_by_skill`, and any removed pack, destination, or legacy evidence.

The manager's individual `--skill` and set-based `--set` or `--skill-set` selectors are obsolete. Use repeated `--pack admin|agent`. Passing a standalone name such as `houmao-shared-routines` to `--pack` fails because it is not a pack selector; passing a child logical id fails because a child is not an install selector. This restriction does not apply to the separate `npx skills` command.

## Ownership Receipt

Each managed target keeps one tool-scoped receipt:

```text
<home>/.houmao/system-skills/<tool>/receipt.json
```

The `houmao-system-skills-receipt.v2` payload records the manifest and package versions, tool, resolved home, collection-wide projection mode, selected packs, update time, and conservatively removed legacy paths. Its `skills` array contains one record per standalone destination:

- standalone name and role;
- home-relative destination;
- `copy` or `symlink` projection mode;
- complete-tree content digest;
- non-empty `owning_pack_ids` set.

One receipt uses one projection mode for its complete collection. An explicit install, sync, or upgrade may transactionally replace every owned member to change mode. Receipt writes are atomic and occur after destination commit.

A missing receipt is `absent`. Invalid JSON or invalid current-version data is `corrupt`. A future schema version is `unsupported`; lifecycle mutation refuses to infer ownership. A v3 composed receipt is `legacy-v3` and its packs report drift until upgrade.

## `status`

Status is read only. It reports receipt state, all six standalone members, both packs, owner sets, expected digests, shared-child completeness, and legacy flat-path evidence:

```bash
houmao-mgr system-skills status --tool codex
houmao-mgr system-skills status --tool codex --home ~/.codex
houmao-mgr --print-json system-skills status --tool kimi
```

Member and pack integrity classes are:

| Status | Meaning |
|---|---|
| `absent` | The receipt does not own the member or pack. |
| `complete` | Every owned static destination has the recorded shape and digest; shared routines contain all sixteen children. |
| `incomplete` | An owned destination or required shared child is missing. |
| `drifted` | Owned content differs from its digest, or a v3 receipt predates the static v4 contract. |
| `conflicting` | A destination has the wrong type, symlink target, or ownership shape. |

Legacy flat-path classifications remain separate from current ownership:

| Classification | Meaning |
|---|---|
| `package-linked` | A symlink targets a known old packaged source. |
| `digest-matched` | A complete copied tree matches a known legacy digest. |
| `modified` | A known legacy path contains different content or points elsewhere. |
| `unknown` | An unrecognized `houmao-*` path exists outside the current six roots. |

Legacy aggregate state is `absent`, `complete`, `partial`, or `conflicting`. Name-only or partial evidence never creates receipt ownership.

## `upgrade`

`upgrade` refreshes selected complete packs through the same receipt-last transaction and conservatively migrates old state:

```bash
houmao-mgr system-skills upgrade --tool codex --home ~/.codex --pack admin
houmao-mgr system-skills upgrade --tool codex --home ~/.codex --pack agent --symlink
```

Omitting `--pack` selects the explicit CLI default `admin`. For a healthy v3 composed receipt, upgrade:

1. parses the old receipt-owned pack and destination evidence;
2. stages the complete v4 static union;
3. replaces the old actor entrypoint destinations;
4. adds `houmao-shared-routines` and both top-level loop siblings;
5. commits and writes the v4 receipt last;
6. removes obsolete receipt-owned materialization data only after commit.

Modified v3 destinations block automatic replacement and remain available for manual comparison. Unknown or unowned paths are preserved. Legacy flat paths are removed only when they are `package-linked` or `digest-matched`; `modified` and `unknown` paths appear in `preserved_legacy_paths`.

Use this breaking-migration sequence:

```bash
houmao-mgr system-skills status --tool codex --home ~/.codex
houmao-mgr system-skills upgrade --tool codex --home ~/.codex --pack admin
houmao-mgr system-skills status --tool codex --home ~/.codex
```

Structured upgrade output adds `legacy_before`, `preserved_legacy_paths`, `migrated_v3`, and `removed_obsolete_paths` to the install result.

## `uninstall`

Uninstall subtracts selected pack ownership. Omission selects every pack currently owned by the receipt:

```bash
houmao-mgr system-skills uninstall --tool codex --pack admin
houmao-mgr system-skills uninstall --tool codex --pack agent
houmao-mgr system-skills uninstall --tool codex
```

When both packs are installed, removing `admin` deletes `houmao-admin-welcome` and `houmao-admin-entrypoint`. Shared routines and both loops remain because `agent` still owns them. The same rule applies in reverse: a shared projection is removed only after its final owning pack is removed.

An ownership-shape conflict is preserved and reported in `preserved_conflicting_paths`. Independently removable destinations may still be removed. Unrelated user skills and unowned legacy paths remain untouched. The receipt disappears when no owned packs remain.

Structured output reports requested, removed, and absent packs; removed destinations; `retained_shared_skills`; preserved conflicts; and the receipt path.

## Managed-Home Policy

Managed launch, rebuild, relaunch, and join use `agent` when policy is omitted. Source policy modes are `default`, `extend`, `replace`, and `none`; profile policy modes are `inherit`, `extend`, `replace`, and `none`.

```yaml
launch:
  system_skills:
    mode: extend
    packs:
      - admin
```

`extend` on a source starts from the managed `agent` default. `replace` selects exactly the listed packs. `none` selects no pack. On a reused home, exact sync removes only receipt-owned members no longer selected and preserves unrelated user skills.

Stored `sets` and `skills` fields are rejected with a migration diagnostic. Complete packs are the only manager selection units.

## Public Invocation Surfaces

Normal actor-aware calls start at an entrypoint:

```text
$houmao-admin-entrypoint credential-mgr list
$houmao-admin-entrypoint agent-definition profiles
$houmao-admin-entrypoint agent-inspect discover for reviewer-1
$houmao-agent-entrypoint agent-email-comms status
$houmao-agent-entrypoint process-emails-via-gateway process-round http://127.0.0.1:43123
```

Advanced direct calls use shared routines. No-frame direct calls default to admin; leading `as-agent` performs fresh self-verification:

```text
$houmao-shared-routines agent-inspect discover for reviewer-1
$houmao-shared-routines as-agent agent-email-comms status
```

Manual loop calls use the top-level loop skills and an explicit `<loop-dir>`:

```text
$houmao-agent-loop-pro init <loop-dir>
$houmao-agent-loop-pro execplan-fast-forward <loop-dir>
$houmao-agent-loop-lite init <loop-dir>
$houmao-agent-loop-lite as-agent status <loop-dir>
```

`houmao-agent-loop-pro` provides schema-rich loop authoring; `houmao-agent-loop-lite` provides Markdown/direct-SQL loop authoring without a generated harness.

Direct calls do not bypass actor eligibility, target rules, identity checks, gates, or stop conditions. Parent-qualified object notation identifies shared children, for example `houmao-shared-routines->houmao-agent-email-comms`.

## Shared Child Inventory

| Logical ID | Eligible Actor | Major Command Family |
|---|---|---|
| `houmao-project-mgr` | Admin | Project initialization, status, launch profiles, easy instances |
| `houmao-credential-mgr` | Admin | Project and native credential operations |
| `houmao-agent-definition` | Admin | Roles, recipes, launch dossiers, specialists, profiles, launch and stop |
| `houmao-operator-messaging` | Admin | Clarify, confirm, and dispatch prompt or mail |
| `houmao-process-emails-via-gateway` | Agent | Prompt-provided gateway mail round |
| `houmao-agent-email-comms` | Admin, Agent | Resolver, scoped mail, gateway API, and transport fallback |
| `houmao-adv-usage-pattern` | Admin, Agent | Self-notification, pairwise, relay, and notifier-loop compositions |
| `houmao-utils-workspace-mgr` | Admin, Agent | Plan, create, validate, and summarize workspaces |
| `houmao-ext-graphing` | Admin, Agent | Plotly and Vega-Lite graphing workflows |
| `houmao-mailbox-mgr` | Admin, Agent | Mailbox roots, registration, binding, cleanup, and export |
| `houmao-memory-mgr` | Admin, Agent | Managed memo read, write, and remove |
| `houmao-agent-instance` | Admin, Agent | Launch, join, list, stop, relaunch, and cleanup |
| `houmao-agent-inspect` | Admin, Agent | Discovery, screen, mailbox, artifacts, and logs |
| `houmao-agent-messaging` | Admin, Agent | Prompt, interrupt, queue, raw input, mail, and reset context |
| `houmao-agent-gateway` | Admin, Agent | Gateway lifecycle, services, reminders, notifier, and watch |
| `houmao-interop-ag-ui` | Admin, Agent | AG-UI validation, framing, rendering, and publishing |

`specialist-mgr` remains an admin and direct-shared compatibility alias. It explains the original specialist route and delegates to `houmao-agent-definition`; it does not own another command tree.

## Breaking Name and Selector Migration

| Removed or Changed Surface | Replacement |
|---|---|
| Manager `--skill <name>` | `--pack admin` or `--pack agent` |
| Manager `--set` / `--skill-set core|extensions|all` | Repeat complete `--pack` selectors |
| Stored `skills:` / `sets:` | Stored `packs:` |
| `$houmao-touring ...` | `$houmao-admin-welcome ...` |
| Old flat `$houmao-specialist-mgr ...` | `$houmao-admin-entrypoint specialist-mgr ...` or `$houmao-shared-routines specialist-mgr ...` |
| Nested pro or lite loop route | Direct top-level loop invocation |
| Bare low-level routine trigger | Actor entrypoint route or advanced shared-routines route |

Old names remain only in migration evidence and the read-only legacy digest inventory. They are not generated compatibility directories.

## Errors and Safety Notes

- Unknown packs fail before multi-target mutation.
- Duplicate tool names and empty comma-separated tool entries fail validation.
- `--home` with multiple tools fails because one path cannot represent several target-native homes.
- Untracked selected-path collisions fail preflight and remain unchanged.
- Corrupt or future-version receipts block lifecycle mutation but remain inspectable through status.
- Modified legacy or v3-owned content is preserved or blocks unsafe replacement.
- Standalone names, child logical ids, and `houmao-auto-system-prompt` cannot be used as manager pack selectors.

## See Also

- [System Skills Overview](../../getting-started/system-skills-overview.md): actor model, guided paths, direct invocation, and installation choices.
- [Easy Specialists](../../getting-started/easy-specialists.md): persisted source pack policy.
- [Launch Profiles](../../getting-started/launch-profiles.md): source/profile policy precedence and reuse.
- [Mailbox Quick Start](../mailbox/quickstart.md): managed mailbox setup and agent-entrypoint routing.
