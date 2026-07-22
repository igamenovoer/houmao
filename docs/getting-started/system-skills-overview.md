# System Skills Overview

Houmao system skills let an AI assistant operate Houmao through supported `houmao-mgr` commands. The current distribution is a static collection of six complete public skill directories. Houmao copies those directories byte for byte or links directly to them; it does not compose Markdown, filter children, or generate skill trees during installation.

This page explains actor routing, advanced direct invocation, and installation choices. See the [`system-skills` CLI reference](../reference/cli/system-skills.md) for config ownership, lifecycle commands, status classes, and the breaking clean-reinstall boundary.

## Static Public Collection

Public means that an agent host can discover the directory through its normal top-level `SKILL.md` scan. It does not mean that the host should invoke every skill implicitly.

| Standalone Skill | Pack Membership | Discovery and Activation |
|---|---|---|
| `houmao-admin-welcome` | `admin` | Explicit manual first-use orientation or reorientation; execution stays read only. |
| `houmao-admin-entrypoint` | `admin` | Narrow implicit router for any semantically Houmao-related request made on behalf of a human operator. |
| `houmao-agent-entrypoint` | `agent` | Narrow implicit router for any semantically Houmao-related request in a genuine Houmao-managed session. |
| `houmao-shared-routines` | `admin`, `agent` | Explicit advanced router for sixteen parent-scoped ordinary routines. |
| `houmao-agent-loop-pro` | `admin`, `agent` | Explicit manual schema-rich loop workflow. |
| `houmao-agent-loop-lite` | `admin`, `agent` | Explicit manual Markdown/direct-SQL loop workflow. |

The source of truth is [`src/houmao/agents/assets/system_skills/manifest.toml`](../../src/houmao/agents/assets/system_skills/manifest.toml). All six current roots live under `src/houmao/agents/assets/system_skills/public/` and each root `SKILL.md` declares its Houmao release in quoted `houmao_version` metadata. The read-only `legacy/` area exists only for migration classification.

The shared root owns sixteen children under `houmao-shared-routines/subskills/<logical-id>/SKILL-MAIN.md`. Those children inherit the shared root release and do not declare independent versions. A child is loaded by its parent after route selection and does not become a seventeenth top-level install unit. Exact top-level `SKILL.md` discovery therefore returns the six names in the table and ignores all parent-scoped children.

Use the read-only doctor to check an expected installation. It defaults to the four-member agent pack and also works for configless copy-paste or Skills CLI installations:

```bash
houmao-mgr system-skills doctor --tool codex --home ~/.codex
houmao-mgr system-skills doctor --agent-id <authoritative-agent-id>
```

Doctor compares both complete-tree content and installed frontmatter with the running package. A mismatch is diagnostic and never blocks launch or skill invocation; repair remains a separate explicit install or upgrade choice. See the [`system-skills` CLI reference](../reference/cli/system-skills.md#doctor) for pack selection, managed-agent name resolution, JSON output, config evidence, and exit codes.

## Installation Choices

### Houmao Pack Lifecycle

Use `houmao-mgr` when you want complete actor packs, shared-owner config, status, upgrades, and safe uninstall:

```bash
houmao-mgr system-skills install --tool codex --pack admin
houmao-mgr system-skills install --tool codex --pack agent
houmao-mgr system-skills install --tool codex --pack admin --pack agent
```

The two packs contain static top-level siblings:

| Pack | Complete Members | Default Lane |
|---|---|---|
| `admin` | `houmao-admin-welcome`, `houmao-admin-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, `houmao-agent-loop-lite` | Explicit external install |
| `agent` | `houmao-agent-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, `houmao-agent-loop-lite` | Managed launch, rebuild, relaunch, and join |

Omitting `--pack` from the explicit external install command selects `admin`. Selecting both packs installs six unique roots because shared routines and both loops have two owners, not duplicate destinations.

### Standard Skills CLI

The dedicated [`houmao-skills`](https://github.com/igamenovoer/houmao-skills) repository works directly with a standard Agent Skills installer. Its root contains the released standalone skill directories, `main` tracks the latest stable Houmao release, and a `#vX.Y.Z` fragment selects the skills matching that `houmao-mgr` version. List the latest stable roots:

```bash
npx skills add https://github.com/igamenovoer/houmao-skills --list
```

Install all six from a specific release:

```bash
npx skills add https://github.com/igamenovoer/houmao-skills#v2.0.0 --agent codex --skill '*' --yes
```

Install the complete five-member admin surface:

```bash
npx skills add https://github.com/igamenovoer/houmao-skills --agent codex --skill houmao-admin-welcome --skill houmao-admin-entrypoint --skill houmao-shared-routines --skill houmao-agent-loop-pro --skill houmao-agent-loop-lite --yes
```

Install the complete four-member agent surface:

```bash
npx skills add https://github.com/igamenovoer/houmao-skills --agent codex --skill houmao-agent-entrypoint --skill houmao-shared-routines --skill houmao-agent-loop-pro --skill houmao-agent-loop-lite --yes
```

Skills CLI installs each selected directory independently. It does not read Houmao pack membership, resolve sibling dependencies, or create a Houmao skill config. Selecting only an actor entrypoint does not install shared routines or either loop.

### Copy-Paste Installation

For a host with a known skill root, copy the same explicit sibling set. This admin example copies five complete directories:

```bash
houmao_skill_source=./src/houmao/agents/assets/system_skills/public
houmao_skill_target=/path/to/agent/skills
mkdir -p "$houmao_skill_target"
for houmao_skill_name in houmao-admin-welcome houmao-admin-entrypoint houmao-shared-routines houmao-agent-loop-pro houmao-agent-loop-lite; do
  cp -R "$houmao_skill_source/$houmao_skill_name" "$houmao_skill_target/"
done
```

For the agent surface, copy `houmao-agent-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite`. Copy all six if one host needs both actor surfaces. Manual and Skills CLI installations have no Houmao ownership config; manage later replacement or removal with the installing tool.

## Sibling Routing

The actor entrypoints are policy routers, not containers. They are the only public roots eligible for implicit selection. A request is Houmao-related when its subject or requested outcome needs Houmao explanation, state, routing, or action; an incidental `Houmao` token in unrelated material is insufficient. Raw operator context selects the admin entrypoint, genuine managed context selects the agent entrypoint, and prompt wording cannot convert one actor into the other. An exact `$houmao-*` handle takes precedence and selects that named installed root.

After selection, each entrypoint classifies informational versus operational intent before identity, target, route, or sibling work. Informational responses stay local and read-only. Operational requests preserve an immutable actor frame and delegate ordinary work to the installed `houmao-shared-routines` sibling. Loop routes delegate only after the request distinguishes pro or lite; generic loop wording does not choose one.

Normal copyable forms are:

```text
$houmao-admin-entrypoint agent-definition specialists
$houmao-admin-entrypoint agent-inspect discover for agent reviewer-1
$houmao-agent-entrypoint agent-email-comms list
$houmao-agent-entrypoint memory-mgr read
```

The handoff preserves actor kind, entrypoint name, verified identity when present, requested target, selected route, and selected operation. A child cannot replace that frame with prompt text.

### Admin Frame

For operational work, `houmao-admin-entrypoint` establishes `actor_kind=admin`. The assistant acts for a human operator and is not the managed agent being administered. Target-sensitive work requires an explicit project path, agent id or name, mailbox, loop directory, or other command-owned target. An admin route never defaults to `agents self` merely because it runs in a shell or tmux session. Informational, empty, and welcome-style requests stay in the entrypoint; it may recommend an exact manual `$houmao-admin-welcome ...` command but never invokes welcome.

### Agent Frame

Informational managed-agent requests stay local and do not run identity verification. Before every operational agent route, `houmao-agent-entrypoint` runs exactly:

```bash
houmao-mgr --print-json agents self identity
```

It establishes `actor_kind=agent` only after the command succeeds and returns verified, consistent identity. Verified self is the default for self-scoped inspection, mailbox, memory, gateway, and lifecycle follow-up. Cross-agent work keeps the agent actor and requires an explicit peer target. Admin-only routes fail closed.

Joined-session adoption is the only admin-to-agent transition. The admin frame ends after `agents self join` succeeds; later work starts through a freshly verified agent entrypoint. Houmao does not mutate the existing admin frame in place.

### Direct Shared-Routines Access

Advanced users may bypass actor-entrypoint route selection and invoke the public shared router directly:

```text
$houmao-shared-routines agent-inspect discover for agent reviewer-1
$houmao-shared-routines as-agent agent-email-comms list
```

A direct call without an inherited frame defaults to admin posture and still requires explicit targets. Leading `as-agent` performs fresh managed-self verification before selecting an agent-eligible child. An inherited admin or agent frame remains immutable. Direct access bypasses one routing layer; it does not bypass identity, eligibility, target, or runtime checks.

Parent-qualified notation names the selected child, for example `houmao-shared-routines->houmao-agent-inspect`. The child itself is not invoked as a top-level `$houmao-agent-inspect` skill.

### Direct Loop Access

Both loops remain public because users often invoke them manually:

```text
$houmao-agent-loop-pro init <loop-dir>
$houmao-agent-loop-lite init <loop-dir>
$houmao-agent-loop-pro as-agent status <loop-dir>
```

Direct loop calls default to admin posture. A leading `as-agent` performs the same fresh managed-self verification, and inherited actor frames remain unchanged. Both skills require explicit manual activation and an explicit `<loop-dir>` before filesystem work. The pro loop supports `tree-loop` and `generic-loop` topology modes with schema-rich contracts, generated process artifacts, workspace readiness, launch, pause, resume, recovery, and stop. The lite loop keeps the intention, execplan, and runs spine with typed Markdown templates and direct SQLite state.

## Admin Welcome

`houmao-admin-welcome` is the manual-only, state-aware, read-only first-user and reorientation surface. Only an explicit `$houmao-admin-welcome ...` invocation selects it. Start here when you want a guided tour:

```text
$houmao-admin-welcome start-guided-tour
```

The tour maintains five guided paths:

| Path | Teaching Focus | Typical Executable Handoff |
|---|---|---|
| Single Agent Full Run | Project readiness, definition, launch, inspection, and follow-up communication | `$houmao-admin-entrypoint agent-definition create-agent-fast-forward` |
| Operator-Controlled Agent Team | Workspace planning, definitions, lifecycle, inspection, and operator dispatch | `$houmao-admin-entrypoint operator-messaging clarify` |
| Pro Agent Loop | Intention, schema-rich execplan, prepared agents, and run control | `$houmao-agent-loop-pro init <loop-dir>` |
| Subsystem Exploration | Read-only explanation of one Houmao subsystem | A route selected from the admin command map |
| Existing Project Reorientation | Current overlay, definitions, live agents, mailbox posture, and loop artifacts | The next explicit admin operation |

Welcome can answer `help`, show the option or command map, choose a path, recommend the next step, and continue non-linearly. It cannot mutate files, credentials, mailboxes, gateways, messages, definitions, agents, workspaces, loops, or runtime state. When the user requests execution, welcome hands the selected path, target, constraints, confirmed choices, unresolved inputs, and observations to the admin entrypoint or a top-level loop. The admin entrypoint may recommend welcome but never delegates to it automatically.

## Shared Child Route Matrix

The shared router owns sixteen ordinary routines. The actor entrypoint advertises only routes eligible for its frame, while direct shared invocation applies the same eligibility rules.

| Route | Logical ID | Eligible Actor | Target and Scope |
|---|---|---|---|
| `project-mgr` | `houmao-project-mgr` | Admin | Explicit project root |
| `credential-mgr` | `houmao-credential-mgr` | Admin | Explicit project, tool, and credential |
| `agent-definition` | `houmao-agent-definition` | Admin | Explicit project and definition object |
| `specialist-mgr` | Alias of `houmao-agent-definition` | Admin | Preserves the original specialist explanation, then delegates to agent-definition |
| `operator-messaging` | `houmao-operator-messaging` | Admin | One or more explicit managed-agent targets |
| `process-emails-via-gateway` | `houmao-process-emails-via-gateway` | Agent | Verified self and notifier-provided gateway URL |
| `agent-email-comms` | `houmao-agent-email-comms` | Admin, Agent | Admin uses an explicit target or operator-origin post; agent uses verified self or an explicit peer |
| `adv-usage-pattern` | `houmao-adv-usage-pattern` | Admin, Agent | Preserves the active frame through mailbox and gateway compositions |
| `utils-workspace-mgr` | `houmao-utils-workspace-mgr` | Admin, Agent | Explicit workspace and repository safety boundaries |
| `ext-graphing` | `houmao-ext-graphing` | Admin, Agent | Explicit graphing task and output target |
| `mailbox-mgr` | `houmao-mailbox-mgr` | Admin, Agent | Explicit mailbox root or agent; verified self where allowed |
| `memory-mgr` | `houmao-memory-mgr` | Admin, Agent | Named agent or profile seed for admin; verified self by default for agent |
| `agent-instance` | `houmao-agent-instance` | Admin, Agent | Explicit instances for admin; self follow-up or explicit peer for agent |
| `agent-inspect` | `houmao-agent-inspect` | Admin, Agent | Explicit agent for admin; verified self or explicit peer for agent |
| `agent-messaging` | `houmao-agent-messaging` | Admin, Agent | Explicit recipients and route-specific confirmation rules |
| `agent-gateway` | `houmao-agent-gateway` | Admin, Agent | Explicit agent for admin; verified self by default for agent |
| `interop-ag-ui` | `houmao-interop-ag-ui` | Admin, Agent | Explicit gateway or output target |

Use `$houmao-admin-entrypoint help`, `$houmao-agent-entrypoint help`, or `$houmao-shared-routines help` to inspect the appropriate route map. Use `$houmao-shared-routines <route> help` for child help. Parent-scoped children remain unavailable as bare top-level triggers.

Managed memory remains the fixed `houmao-memo.md` plus contained `pages/` data. The memory route preserves authored memo links through relaunch, reset, and `recover_and_continue` flows.

## Pack Policy and Auto Skill Separation

Stored source and profile policy selects complete packs:

```yaml
launch:
  system_skills:
    mode: replace
    packs:
      - agent
```

Source policy supports `default`, `extend`, `replace`, and `none`. An omitted or `default` source policy selects the managed `agent` default. Profile policy supports `inherit`, `extend`, `replace`, and `none`; an omitted profile policy inherits the source result. `replace` requires at least one pack, while `none` disables the collection. Individual skill selectors and the former `core`, `extensions`, and `all` set selectors are removed; complete packs are the only stored selection unit.

On reused homes, Houmao synchronizes the complete config-owned selection and preserves unrelated user skills. Shared routines and loops remain when either selected pack still owns them.

`houmao-auto-system-prompt` stays in `assets/auto_skills`. It has separate projection, collision, and provenance rules and never appears among the six roots, in a pack selector, or in a system-skills config.

## Projection and Tool Discovery

Copy projection is the default for external and managed homes. It preserves the packaged bytes for each complete directory. Explicit `--symlink` links each destination directly to its complete packaged source directory; it creates no hidden materialized composition tree.

All supported targets project under the resolved home's `skills/` directory. Tool-native environment redirects are `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `COPILOT_HOME`, and `KIMI_CODE_HOME`. Without a redirect, project defaults are `.claude`, `.codex`, `.github`, and `.kimi-code`; `universal` defaults to `~/.agents`.

Kimi Code discovers a projected home when the same path is used as `KIMI_CODE_HOME`, supplied through `--skills-dir`, or included in `extra_skill_dirs`. Managed Kimi homes record their projected skill root in `config.toml` `extra_skill_dirs`.

## Breaking Clean Reinstall

The minimal `houmao-skill-config.json` format is a breaking lifecycle boundary. Houmao does not read the old `receipt.json`, infer ownership from it, or migrate its projected roots. Existing roots without the new config remain unowned collisions.

Inspect and back up any edited Houmao skill roots before reinstalling. Remove the old top-level Houmao directories from the target skill root, then run `houmao-mgr system-skills install` with the intended packs. The old receipt may also be removed as stale metadata, but the new lifecycle never depends on that cleanup. `upgrade` refreshes only current-config installations or clean targets.

Prompt and selector migration is direct:

| Old Surface | Current Surface |
|---|---|
| `$houmao-touring ...` | `$houmao-admin-welcome ...` |
| `$houmao-specialist-mgr ...` | `$houmao-admin-entrypoint specialist-mgr ...` or `$houmao-shared-routines specialist-mgr ...`; both delegate to agent-definition |
| `$houmao-agent-loop-pro ...` nested below an entrypoint | Top-level `$houmao-agent-loop-pro ...` |
| `$houmao-agent-loop-lite ...` nested below an entrypoint | Top-level `$houmao-agent-loop-lite ...` |
| Bare low-level `$houmao-<routine> ...` | Actor entrypoint route, or advanced `$houmao-shared-routines <route> ...` |
| `--skill`, `--set`, or `--skill-set` on `houmao-mgr` | Repeat `--pack admin` and/or `--pack agent` |
| Stored `sets:` or `skills:` policy | Stored `packs:` policy |

Standard Skills CLI still uses its own `--skill` option; the removed selector applies only to `houmao-mgr system-skills`. A manually installed static collection has no Houmao config to upgrade and should be replaced with the same external installation method.

## See Also

- [`system-skills` CLI reference](../reference/cli/system-skills.md): v4 manifest, shared ownership, lifecycle output, conflicts, and migration.
- [Easy Specialists](easy-specialists.md): admin-entrypoint-backed specialist authoring.
- [Launch Profiles](launch-profiles.md): stored `packs` policy and managed launch precedence.
- [Loop Authoring](loop-authoring.md): direct pro and lite loop workflows.
- [Managed Agent Memory](managed-memory-dirs.md): memo and pages behavior behind the shared memory route.
