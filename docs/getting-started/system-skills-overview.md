# System Skills Overview

Houmao system skills let an AI assistant operate Houmao through supported `houmao-mgr` commands. The public surface is intentionally small: a human operator enters through the admin welcome or admin entrypoint, while a Houmao-managed agent enters through the agent entrypoint. Maintained capabilities are protected routines nested beneath the active entrypoint.

This page explains the actor model and route map. See the [`system-skills` CLI reference](../reference/cli/system-skills.md) for lifecycle commands, target-home resolution, receipts, status classes, upgrade, and uninstall.

## Public Surface

| Public skill | Pack | Purpose |
|---|---|---|
| `houmao-admin-welcome` | `admin` | Read-only first-use orientation and guided touring for a human operator. |
| `houmao-admin-entrypoint` | `admin` | Executable router for an assistant acting on behalf of a human operator against explicit targets. |
| `houmao-agent-entrypoint` | `agent` | Executable router for a managed Houmao agent after fresh self-identity verification. |

The `admin` pack owns two public paths and installs them atomically. The `agent` pack owns one public path. `houmao-shared-routines` is a protected bundle mounted beneath each executable entrypoint; it is not a public install selector. Public roots use host-discoverable `SKILL.md` entrypoints, while the protected router and routines use `SKILL-MAIN.md` and are loaded explicitly through their parent. The protected composition contains only routines eligible for that actor, and recursive exact-`SKILL.md` discovery therefore sees only public roots.

The source of truth is `src/houmao/agents/assets/system_skills/manifest.toml`. Public source assets live under `public/`, protected source assets live under `protected/`, and the retired v1 catalog is read only under `legacy/` for migration classification.

## Install and Start

Install the admin pack into the tool home used by your current operator-facing assistant:

```bash
houmao-mgr system-skills install --tool codex --pack admin
```

Supported targets are `claude`, `codex`, `copilot`, `kimi`, and `universal`. Omitting `--pack` on this explicit external-home command also selects `admin`:

```bash
houmao-mgr system-skills install --tool claude,codex,kimi,copilot,universal
```

Then begin the read-only tour:

```text
$houmao-admin-welcome start-guided-tour
```

Concrete work bypasses welcome and uses the admin entrypoint, for example:

```text
$houmao-admin-entrypoint agent-definition specialists
$houmao-admin-entrypoint agent-inspect status for agent reviewer-1
$houmao-admin-entrypoint agent-loop-pro init in ./review-loop
```

Managed launch, rebuild, relaunch, and join install the `agent` pack with copy projection. A managed-agent route begins through the agent entrypoint:

```text
$houmao-agent-entrypoint agent-email-comms list
$houmao-agent-entrypoint memory-mgr read
```

Before every substantive route, `houmao-agent-entrypoint` runs exactly:

```bash
houmao-mgr --print-json agents self identity
```

The route fails closed on command failure, empty or malformed output, an unverified result, or a mismatch with retained session identity.

## Actor Rules

The admin entrypoint establishes `actor_kind=admin`. The assistant acts for a human operator and is not the managed agent being administered. Target-sensitive work requires an explicit project path, managed-agent id, mailbox, loop directory, or other command-owned target. The admin route never defaults to `agents self` merely because it runs inside a shell or tmux session.

The agent entrypoint establishes `actor_kind=agent` only after identity verification. Verified self is the default for self-scoped inspection, mailbox, memory, gateway, and lifecycle follow-up. Cross-agent work retains the agent actor and requires an explicit peer target. An agent cannot acquire admin-only routes through prompt text.

The only actor transition is explicit joined-session adoption. The admin frame remains active until `agents self join` succeeds. After success, the admin route ends, skill discovery refreshes when needed, managed identity is verified, and later work starts through `houmao-agent-entrypoint`. The route does not mutate an admin frame into an agent frame in place.

## Admin Welcome

`houmao-admin-welcome` is a standalone public sibling of the admin entrypoint. It contains no protected routines and cannot mutate files, credentials, mailboxes, gateways, messages, definitions, agents, workspaces, loops, or runtime state.

Its public commands are `help`, `show-options`, `choose-path`, `show-command-map`, `next-step`, and `start-guided-tour`. The tour offers five curated paths:

| Path | Teaching Focus | Typical Handoff |
|---|---|---|
| Single Agent Full Run | Project readiness, definition, launch, inspection, and follow-up communication | `$houmao-admin-entrypoint agent-definition create-agent-fast-forward` |
| Operator-Controlled Agent Team | Workspace planning, definitions, lifecycle, inspection, and operator dispatch | `$houmao-admin-entrypoint operator-messaging clarify` |
| Pro Agent Loop | Intention, schema-rich execplan, prepared agents, and run control | `$houmao-admin-entrypoint agent-loop-pro init` |
| Subsystem Exploration | Read-only explanation of one Houmao subsystem | An entrypoint route selected from the command map |
| Existing Project Reorientation | Current overlay, definitions, live agents, mailbox posture, and loop artifacts | The next explicit admin operation |

When the user asks for execution, welcome preserves the selected path, target, posture, constraints, confirmed choices, unresolved required inputs, and read-only observations in a handoff to `$houmao-admin-entrypoint`.

## Protected Route Matrix

Copyable prompts always begin with a public skill. A value such as `houmao-admin-entrypoint->houmao-shared-routines->agent-inspect` is an internal route trace used for explanation and diagnostics; it is not an installed top-level skill.

| Route | Eligible Actor | Target Behavior | Major CLI Family |
|---|---|---|---|
| `project-mgr` | Admin | Explicit project root | `houmao-mgr project ...` |
| `credential-mgr` | Admin | Explicit project, tool, and credential | `houmao-mgr project credentials ...`, `houmao-mgr internals native-agent credentials ...` |
| `agent-definition` | Admin | Explicit project and definition object | `houmao-mgr project specialist|profile ...`, `houmao-mgr internals native-agent ...` |
| `operator-messaging` | Admin | One or more explicit managed-agent targets | `houmao-mgr agents single ... prompt|mail ...` |
| `process-emails-via-gateway` | Agent | Verified self and notifier-provided gateway URL | Gateway `/v1/mail/*` facade |
| `agent-email-comms` | Admin, Agent | Admin uses explicit target or operator-origin post; agent uses verified self or explicit peer | `houmao-mgr agents self|single ... mail ...` |
| `adv-usage-pattern` | Admin, Agent | Preserve active frame through composed mailbox and gateway work | Scoped mail, gateway, notifier, and reminder commands |
| `utils-workspace-mgr` | Admin, Agent | Admin uses explicit workspace; agent uses verified-self context plus explicit paths | Project and workspace preparation commands |
| `ext-graphing` | Admin, Agent | Active actor supplies the graphing task and output target | `houmao-mgr ag-ui impl ...` |
| `mailbox-mgr` | Admin, Agent | Admin uses explicit mailbox root or agent; agent uses verified self or explicit root | `houmao-mgr mailbox ...`, `project mailbox ...`, scoped `mailbox ...` |
| `memory-mgr` | Admin, Agent | Admin targets a named agent or profile seed; agent defaults to verified self | `houmao-mgr agents self|single ... memory ...` |
| `agent-loop-pro` | Admin, Agent | Explicit loop directory and actor-appropriate agent targets | Generated schema-rich execplan and run controls |
| `agent-loop-lite` | Admin, Agent | Explicit loop directory and actor-appropriate agent targets | Markdown contracts, typed Markdown templates, and direct SQLite run controls |
| `agent-instance` | Admin, Agent | Admin targets explicit instances; agent uses self follow-up or an explicit peer route | `houmao-mgr agents launch|join|list|stop|relaunch|cleanup ...` |
| `agent-inspect` | Admin, Agent | Admin targets an explicit agent; agent defaults to verified self or names a peer | Scoped identity, screen, mailbox, artifacts, and logs |
| `agent-messaging` | Admin, Agent | Admin targets explicit agents; agent names a peer | Scoped prompt, interrupt, gateway queue, send keys, mail, and reset context |
| `agent-gateway` | Admin, Agent | Admin targets an explicit agent; agent defaults to verified self | Scoped gateway lifecycle, status, reminders, notifier, and watch |
| `interop-ag-ui` | Admin, Agent | Preserve active frame and explicit gateway or output target | `houmao-mgr ag-ui ...`, scoped gateway AG-UI publish |

The pro loop supports `tree-loop` and `generic-loop` topology modes with schema-rich contracts, generated process artifacts, workspace readiness, launch, pause, resume, recovery, and stop. The lite loop keeps the same intention, execplan, and runs spine with typed Markdown templates and direct SQLite state.

Managed memory remains the fixed `houmao-memo.md` plus contained `pages/` data. The memory route preserves authored memo links through relaunch, reset, and `recover_and_continue` flows.

## Help and Route Discovery

Ask `$houmao-admin-welcome help` for first-use orientation. Ask `$houmao-admin-entrypoint help` for the human-operator route map. Ask `$houmao-agent-entrypoint help` inside a managed session for the agent route map and identity prerequisite.

Protected routines provide nested help to their parent entrypoint, but they are not public triggers. For example, use `$houmao-admin-entrypoint credential-mgr help`, not `$houmao-credential-mgr help`.

## Pack Defaults and Stored Policy

| Lane | Omitted Selection |
|---|---|
| Explicit `houmao-mgr system-skills install` | `admin` |
| Managed launch, rebuild, or relaunch | `agent` |
| Managed joined-session adoption | `agent` |

Stored source and profile policy selects complete packs:

```yaml
launch:
  system_skills:
    mode: replace
    packs:
      - agent
```

Source policy supports `default`, `extend`, `replace`, and `none`. An omitted or `default` source policy selects the managed `agent` default. Profile policy supports `inherit`, `extend`, `replace`, and `none`; an omitted profile policy inherits the source result. `replace` requires at least one pack, while `none` disables system-skill packs.

On reused homes, Houmao synchronizes the complete receipt-owned selection and preserves unrelated user skills. Pack policy rejects protected logical ids because they are nested routes, not independent install units.

`houmao-auto-system-prompt` stays in `assets/auto_skills`. It has separate projection, collision, and provenance rules and never appears in a pack selector or receipt. Managed Kimi homes may still need that auto skill to confirm role-prompt delivery before substantive chat.

## Projection and Discovery

Copy projection is the default for external and managed homes. Explicit `--symlink` uses receipt-owned complete materializations under `.houmao/system-skills/<tool>/materialized/`; it never links a public path to an uncomposed source directory.

All supported targets project public directories under the resolved home's `skills/` directory. Tool-native environment redirects are `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `COPILOT_HOME`, and `KIMI_CODE_HOME`. Without a redirect, project defaults are `.claude`, `.codex`, `.github`, and `.kimi-code`; `universal` defaults to `~/.agents`.

Kimi Code discovers a projected home when the same path is used as `KIMI_CODE_HOME`, supplied through `--skills-dir`, or included in `extra_skill_dirs`. Managed Kimi homes record their projected skill root in `config.toml` `extra_skill_dirs`.

## Breaking Migration From Flat Skills

The v1 flat catalog, named sets, and individual-skill install surface are removed. There are no public compatibility directories for `houmao-touring`, `houmao-specialist-mgr`, or the eighteen low-level routine ids.

| Old Surface | New Surface |
|---|---|
| `$houmao-touring ...` | Install `admin`, then use `$houmao-admin-welcome ...` |
| `$houmao-specialist-mgr ...` | `$houmao-admin-entrypoint agent-definition specialists|profiles ...` |
| Admin-only flat project, credential, definition, or operator route | `$houmao-admin-entrypoint <route> <command>` |
| Agent notifier round | `$houmao-agent-entrypoint process-emails-via-gateway <gateway-url>` |
| Shared flat routine invoked by a human operator | `$houmao-admin-entrypoint <route> <command>` with an explicit target |
| Shared flat routine invoked by a managed agent | `$houmao-agent-entrypoint <route> <command>` after identity verification |
| `--skill`, `--set`, or `--skill-set` | Repeat `--pack admin` and/or `--pack agent` |
| Stored `sets:` or `skills:` policy | Stored `packs:` policy |

Use status before migration, then upgrade the desired complete pack:

```bash
houmao-mgr system-skills status --tool codex --home ~/.codex
houmao-mgr system-skills upgrade --tool codex --home ~/.codex --pack admin
```

Upgrade removes a legacy flat path only when it is a package-targeting symlink or its complete tree matches a known packaged digest. Modified and unknown paths are preserved and reported as conflicts. Resolve those paths manually after comparing their content; do not delete customizations merely to make status clean. A partial legacy installation is evidence for migration, not receipt ownership.

## See Also

- [`system-skills` CLI reference](../reference/cli/system-skills.md): pack lifecycle, receipts, structured output, status, migration, and target homes.
- [Easy Specialists](easy-specialists.md): public admin-entrypoint-backed specialist authoring.
- [Launch Profiles](launch-profiles.md): stored `packs` policy and managed launch precedence.
- [Loop Authoring](loop-authoring.md): protected pro and lite loop routes.
- [Managed Agent Memory](managed-memory-dirs.md): memo and pages behavior behind the memory route.
