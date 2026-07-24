# `system-skills`

`houmao-mgr system-skills` installs, diagnoses, inspects, upgrades, and removes complete Houmao actor packs in external or project-scoped tool homes. Managed launch and join use the same static pack lifecycle internally.

```text
houmao-mgr system-skills list
houmao-mgr system-skills install --tool <target> [--home <path>] [--pack admin|agent]... [--symlink]
houmao-mgr system-skills status --tool <target> [--home <path>]
houmao-mgr system-skills doctor --tool <target> [--home <path>] [--pack admin|agent]...
houmao-mgr system-skills doctor (--agent-id <id> | --agent-name <unique-name>) [--pack admin|agent]...
houmao-mgr system-skills upgrade --tool <target> [--home <path>] [--pack admin|agent]... [--symlink]
houmao-mgr system-skills uninstall --tool <target> [--home <path>] [--pack admin|agent]...
```

Use the root `--print-json` flag before `system-skills` for structured output:

```bash
houmao-mgr --print-json system-skills list
houmao-mgr --print-json system-skills status --tool codex --home ~/.codex
houmao-mgr --print-json system-skills doctor --agent-id <id>
```

There is no `system-skills help` subcommand. Skill-level help comes from `$houmao-admin-welcome help`, `$houmao-admin-entrypoint help`, `$houmao-agent-entrypoint help`, `$houmao-shared-routines help`, or either top-level loop's `help` operation.

## V4 Static Collection and Pack Membership

The `houmao-system-skills.v4` manifest records six standalone source directories. Each one has a role, activation posture, pack owners, commands, aliases, dependencies, and a complete source path. It also records sixteen parent-scoped children owned by shared routines, including actor eligibility, route name, dependencies, commands, and aliases.

| Pack | Audience | Static Top-Level Members | Default Lane |
|---|---|---|---|
| `admin` | Human operator | `houmao-admin-welcome`, `houmao-admin-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, `houmao-agent-loop-lite` | Explicit CLI install |
| `agent` | Managed Houmao agent | `houmao-agent-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, `houmao-agent-loop-lite` | Managed launch, rebuild, relaunch, and join |

`houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite` belong to both packs. A combined install has six unique destinations and records both owners on those three shared records.

The two actor entrypoints use narrow implicit activation. `houmao-admin-entrypoint` handles semantically Houmao-related requests in a raw human-operator context, and `houmao-agent-entrypoint` handles them in a genuine managed-agent context. `houmao-admin-welcome`, `houmao-shared-routines`, and both loop roots remain explicit-only. Exact `$houmao-*` handles take precedence over implicit discovery. In a combined installation, current execution context selects the actor entrypoint; prompt claims cannot turn a raw operator into managed self or a managed agent into admin.

The sixteen shared children use `SKILL-MAIN.md` below `houmao-shared-routines/subskills/`. They are route targets, not top-level install members. `houmao-auto-system-prompt` is a separate managed auto skill and never appears in the v4 manifest, skill config, or public-root inventory.

## Top-Level Release Metadata

Each of the six standalone public `SKILL.md` roots declares one quoted `houmao_version` equal to the Houmao project release. The value identifies the checked-in static tree that a copy-paste installer, Skills CLI, or Houmao lifecycle projects without rendering. Release validation compares all six source values with `[project].version` before local distribution builds and tagged publication.

The sixteen `SKILL-MAIN.md` children do not declare independent versions. `houmao-shared-routines/SKILL.md` is the release authority for the complete shared tree. Legacy skills, generated execplan skills, project-authored skills, and the separate `houmao-auto-system-prompt` asset remain outside this contract.

Three values answer different questions:

| Evidence | Meaning |
|---|---|
| Installed `houmao_version` | Release string declared by the installed top-level `SKILL.md`; doctor uses this as observed version evidence. |
| Config `houmao_version` | Houmao package release recorded by the last lifecycle mutation; it does not replace installed frontmatter evidence. |
| Content digest | Exact complete-tree compatibility with the running packaged source, including commands, assets, scripts, references, and shared children. |

Version metadata is diagnostic only. Install, sync, status, upgrade, managed launch, rebuild, relaunch, join, runtime authorization, generated prompts, and skill invocation do not reject a root because its version is old, missing, or malformed.

## Standard External Installation

The dedicated [`houmao-skills`](https://github.com/igamenovoer/houmao-skills) repository is a valid static Agent Skills collection whose skill directories live at repository root. Its unqualified URL selects the latest stable release from `main`; append a matching release tag such as `#v2.1.0` to install the system skills for a specific `houmao-mgr` version. A standard Skills CLI can list or install it without running Houmao's manager:

```bash
npx skills add https://github.com/igamenovoer/houmao-skills --list
npx skills add https://github.com/igamenovoer/houmao-skills#v2.1.0 --agent codex --skill '*' --yes
```

Select all five admin siblings explicitly:

```bash
npx skills add https://github.com/igamenovoer/houmao-skills --agent codex --skill houmao-admin-welcome --skill houmao-admin-entrypoint --skill houmao-shared-routines --skill houmao-agent-loop-pro --skill houmao-agent-loop-lite --yes
```

Select all four agent siblings explicitly:

```bash
npx skills add https://github.com/igamenovoer/houmao-skills --agent codex --skill houmao-agent-entrypoint --skill houmao-shared-routines --skill houmao-agent-loop-pro --skill houmao-agent-loop-lite --yes
```

Skills CLI and copy-paste installation treat each directory independently. They do not resolve Houmao dependencies, create shared owner sets, or write a Houmao skill config. Selecting an entrypoint alone therefore produces an incomplete actor surface. Use `houmao-mgr system-skills` when you want automatic pack closure and config-backed lifecycle management.

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

Before mutation, installation resolves a deduplicated static union, checks every destination for unowned collisions, stages complete directories, validates the union, and backs up replaceable config-owned state. It commits all destinations and writes the config last. A failure restores the prior paths and config. Unrelated user skills remain untouched.

Structured install output reports `tool`, `home_path`, `selected_packs`, `standalone_skills`, `projected_relative_dirs`, `config_path`, `projection_mode`, `owning_pack_ids_by_skill`, and any removed pack, destination, or legacy evidence.

The manager's individual `--skill` and set-based `--set` or `--skill-set` selectors are obsolete. Use repeated `--pack admin|agent`. Passing a standalone name such as `houmao-shared-routines` to `--pack` fails because it is not a pack selector; passing a child logical id fails because a child is not an install selector. This restriction does not apply to the separate `npx skills` command.

## Minimal Skill Config

Each manager-owned target keeps one tool-scoped config:

```text
<home>/.houmao/system-skills/<tool>/houmao-skill-config.json
```

The `houmao-skill-config.v1` payload has exactly four top-level fields:

- `schema_version`: the literal `houmao-skill-config.v1`;
- `houmao_version`: the Houmao release that performed the last lifecycle mutation;
- `projection_mode`: `copy` or `symlink` for the whole collection;
- `skills`: the manifest-ordered standalone destination records.

Each skill record has exactly `name`, `relative_path`, `content_digest`, and a non-empty `owning_pack_ids` list. The manager derives selected packs from the owner union; it does not serialize `selected_packs`, tool, home, timestamps, roles, manifest versions, or source paths. Tool and home come from the config location.

One config uses one projection mode for its complete collection. An explicit install, sync, or upgrade may transactionally replace every owned member to change mode. Config writes are atomic and occur after destination commit.

A missing config is `absent`. Invalid JSON, unknown or missing fields, unsafe paths, duplicate records, invalid digests, invalid owners, or a union that differs from the derived packs is `corrupt`. A future schema version is `unsupported`. Lifecycle mutation refuses to infer ownership from corrupt, unsupported, or absent config state.

## `status`

Status is read only. It reports config state, all six standalone members, both packs, owner sets, expected digests, shared-child completeness, and legacy flat-path evidence:

```bash
houmao-mgr system-skills status --tool codex
houmao-mgr system-skills status --tool codex --home ~/.codex
houmao-mgr --print-json system-skills status --tool kimi
```

Member and pack integrity classes are:

| Status | Meaning |
|---|---|
| `absent` | The config does not own the member or pack. |
| `complete` | Every owned static destination has the recorded shape and digest; shared routines contain all sixteen children. |
| `incomplete` | An owned destination or required shared child is missing. |
| `drifted` | Config-owned content differs from its recorded or packaged digest. |
| `conflicting` | A destination has the wrong type, symlink target, or ownership shape. |

Legacy flat-path classifications remain separate from current ownership:

| Classification | Meaning |
|---|---|
| `package-linked` | A symlink targets a known old packaged source. |
| `digest-matched` | A complete copied tree matches a known legacy digest. |
| `modified` | A known legacy path contains different content or points elsewhere. |
| `unknown` | An unrecognized `houmao-*` path exists outside the current six roots. |

Legacy aggregate state is `absent`, `complete`, `partial`, or `conflicting`. Name-only or partial evidence never creates config ownership.

## `doctor`

Doctor is a read-only check of an explicit expected pack. Omitted `--pack` selects `agent`; repeat the option to inspect a combined six-root installation. Direct-home mode accepts exactly one supported tool and uses the same `--home`, environment redirect, and project-default resolution as lifecycle commands:

```bash
houmao-mgr system-skills doctor --tool codex
houmao-mgr system-skills doctor --tool codex --home ~/.codex --pack agent
houmao-mgr system-skills doctor --tool codex --home ~/.codex --pack admin --pack agent
houmao-mgr --print-json system-skills doctor --tool universal --home ~/.agents --pack admin
```

A complete copy-paste or Skills CLI installation can be healthy without a Houmao skill config. Doctor reads each installed top-level `SKILL.md`, checks its complete tree against the running package, and requires the exact sixteen shared child entrypoints when shared routines is expected. Config status and config `houmao_version` appear as separate supporting evidence.

Managed-agent mode resolves a known local registry record, its session manifest, its brain manifest, the recorded tool, and the persistent home. It does not require a live gateway, lease, tmux session, or provider TUI, so a stopped agent remains diagnosable while those authority files and its home remain readable:

```bash
houmao-mgr system-skills doctor --agent-id <authoritative-agent-id>
houmao-mgr system-skills doctor --agent-name HOUMAO-reviewer
houmao-mgr --print-json system-skills doctor --agent-id <authoritative-agent-id>
```

Friendly names must resolve to exactly one local record. Use `--agent-id` when a name is ambiguous. Agent selectors cannot be combined with `--tool` or `--home`, and external communication-only agents are not valid doctor targets.

Each member reports integrity independently as `absent`, `complete`, `incomplete`, `drifted`, or `conflicting`. Its version status is one of `match`, `mismatch`, `missing`, `invalid`, or `unavailable`. A matching version does not hide edited content, and a config `houmao_version` does not substitute for missing installed metadata. A running version of `0+unknown` produces `unavailable` rather than a false match.

Doctor exits with code 0 only when every expected root has current complete content and a matching version. It emits the full diagnostic and exits with code 1 for health failures. Invalid selectors and unresolved targets use Click exit code 2. Doctor never installs, upgrades, repairs, launches, or writes a config. After a mismatch, choose a separate explicit install or upgrade only after reviewing the reported content and ownership evidence.

## `upgrade`

`upgrade` refreshes selected complete packs through the same config-last transaction:

```bash
houmao-mgr system-skills upgrade --tool codex --home ~/.codex --pack admin
houmao-mgr system-skills upgrade --tool codex --home ~/.codex --pack agent --symlink
```

Omitting `--pack` selects the explicit CLI default `admin`. Upgrade accepts a current `houmao-skill-config.v1` installation or a clean target with no selected destinations. It stages the complete static union, replaces only config-owned destinations, commits destinations, and writes the config last. Legacy flat paths are removed only when they are `package-linked` or `digest-matched`; `modified` and `unknown` paths appear in `preserved_legacy_paths`.

This config change is a breaking lifecycle boundary. The manager does not read, migrate, remove, or use an old `receipt.json` to infer ownership. Old projected top-level roots therefore remain unowned collisions. To reinstall, first inspect and back up any edited roots, remove the old Houmao top-level skill directories from the target skill root, and then run `install` with the intended pack selection. Removing the old receipt is optional because the new lifecycle ignores it, but doing so avoids leaving misleading stale metadata. Do not expect `upgrade` to convert the old installation.

Structured upgrade output adds `legacy_before` and `preserved_legacy_paths` to the install result.

## `uninstall`

Uninstall subtracts selected pack ownership. Omission selects every pack currently owned by the config:

```bash
houmao-mgr system-skills uninstall --tool codex --pack admin
houmao-mgr system-skills uninstall --tool codex --pack agent
houmao-mgr system-skills uninstall --tool codex
```

When both packs are installed, removing `admin` deletes `houmao-admin-welcome` and `houmao-admin-entrypoint`. Shared routines and both loops remain because `agent` still owns them. The same rule applies in reverse: a shared projection is removed only after its final owning pack is removed.

An ownership-shape conflict is preserved and reported in `preserved_conflicting_paths`. Independently removable destinations may still be removed. Unrelated user skills and unowned legacy paths remain untouched. The config disappears when no owned packs remain.

Structured output reports requested, removed, and absent packs; removed destinations; `retained_shared_skills`; preserved conflicts; and the config path.

## Managed-Home Policy

Managed launch, rebuild, relaunch, and join use `agent` when policy is omitted. Source policy modes are `default`, `extend`, `replace`, and `none`; profile policy modes are `inherit`, `extend`, `replace`, and `none`.

```yaml
launch:
  system_skills:
    mode: extend
    packs:
      - admin
```

`extend` on a source starts from the managed `agent` default. `replace` selects exactly the listed packs. `none` selects no pack. On a reused home, exact sync removes only config-owned members no longer selected and preserves unrelated user skills.

Stored `sets` and `skills` fields are rejected with a migration diagnostic. Complete packs are the only manager selection units.

## Public Invocation Surfaces

Natural Houmao-related requests may select the matching actor entrypoint without a skill handle. Each entrypoint classifies informational versus operational intent first. Informational requests stay local; the managed entrypoint does not verify identity for them. Operational managed requests run the exact fresh self-identity command before substantive routing. Missing targets remain post-activation gates.

Explicit actor-aware calls start at an entrypoint:

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

Welcome is also manual-only: use `$houmao-admin-welcome start-guided-tour` when a human operator wants guided orientation. A natural welcome-style question selects the admin entrypoint, which answers concise information locally and may recommend that command without invoking it.

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
- Corrupt or future-version configs block lifecycle mutation but remain inspectable through status.
- Old receipt-era roots remain unowned collisions until the user performs a clean reinstall.
- Standalone names, child logical ids, and `houmao-auto-system-prompt` cannot be used as manager pack selectors.

## See Also

- [System Skills Overview](../../getting-started/system-skills-overview.md): actor model, guided paths, direct invocation, and installation choices.
- [Easy Specialists](../../getting-started/easy-specialists.md): persisted source pack policy.
- [Launch Profiles](../../getting-started/launch-profiles.md): source/profile policy precedence and reuse.
- [Mailbox Quick Start](../mailbox/quickstart.md): managed mailbox setup and agent-entrypoint routing.
