# System Skills Overview

Houmao installs packaged "system skills" into agent tool homes so the **agent itself** can drive Houmao management without the operator running `houmao-mgr` commands by hand. When an agent inside a managed home is asked to "create a new specialist," "send mail to another managed agent," or "attach a gateway," it discovers the right Houmao-owned skill, follows that skill's guidance, and routes through the supported `houmao-mgr` surface.

This page is the **narrative tour**. For the per-flag CLI surface, see the [`system-skills` CLI reference](../reference/cli/system-skills.md). For the 60-second view, see the system-skills subsection in the [project README](https://github.com/igamenovoer/houmao#system-skills-agent-self-management).

```
catalog → narrative → reference

   README                this page                  CLI reference
 (one-line               (5-minute walk-          (every flag,
  per skill)              through, when            every set,
                          each fires)              effective home)
```

## What System Skills Are

Each system skill ships as a directory under `src/houmao/agents/assets/system_skills/<skill-name>/` with a top-level `SKILL.md` and supporting reference material. The packaged catalog at `src/houmao/agents/assets/system_skills/catalog.toml` declares which skills exist, which **named sets** group them, and which sets are auto-installed by managed launches and joins versus selected by explicit `system-skills install` invocations.

System skills are not Python plugins, MCP servers, or runtime hooks. They are agent-readable instruction packages that guide the agent toward the right `houmao-mgr` command for the task. The supporting code is whatever `houmao-mgr` already exposes through `srv_ctrl/commands/`.

## The Packaged Skills

Houmao currently ships the set of system skills declared in `src/houmao/agents/assets/system_skills/catalog.toml`. They split into five concern groups: **guided touring**, **project, specialist, and credential authoring**, **agent definition and instance management**, **agent inspection, communication, gateway, and mailbox**, and **loop authoring and master-run control**.

### Guided Touring

| Skill | What it enables | Canonical CLI routing |
|---|---|---|
| `houmao-touring` | Manual guided tour for first-time or re-orienting users. It starts from current state, explains the next likely branches, and helps the user move across project setup, mailbox setup, specialist/profile authoring, launches, live-agent operations, and lifecycle follow-up. Use it only when the user explicitly asks for the tour. | Routes through the maintained `houmao-mgr project ...`, `houmao-mgr project mailbox ...`, `houmao-mgr project easy ...`, and `houmao-mgr agents ...` families via the dedicated Houmao-owned skills |

### Project, specialist, and credential authoring

| Skill | What it enables | Canonical CLI routing |
|---|---|---|
| `houmao-project-mgr` | Project overlay lifecycle, `.houmao/` layout explanation, project-aware command-effect guidance, explicit launch-profile management, and project-scoped easy-instance inspection or stop routing. | `houmao-mgr project init`, `houmao-mgr project status`, `houmao-mgr project agents launch-profiles ...`, `houmao-mgr project easy instance list|get|stop` |
| `houmao-specialist-mgr` | Create, list, inspect, remove easy specialists; create, list, inspect, remove easy profiles; launch and stop easy instances from either source. | `houmao-mgr project easy specialist ...`, `houmao-mgr project easy profile ...`, `houmao-mgr project easy instance launch|stop` |
| `houmao-credential-mgr` | Add, update, inspect, rename, and remove credentials for Claude, Codex, and Gemini in either the active project overlay or an explicit plain agent-definition directory. Manages credential contents and names, not stored profile-level auth overrides. | `houmao-mgr project credentials <tool> list|get|add|set|rename|remove` / `houmao-mgr credentials <tool> ... --agent-def-dir <path>` |

### Agent definition and instance management

| Skill | What it enables | Canonical CLI routing |
|---|---|---|
| `houmao-agent-definition` | Low-level project-local role and recipe management. Use this when the right move is editing roles or named recipes instead of going through the easy specialist surface. | `houmao-mgr project agents roles ...`, `houmao-mgr project agents recipes ...` (with `presets ...` as the compatibility alias) |
| `houmao-agent-instance` | Launch, adopt (`join`), list, stop, relaunch, and clean up live managed-agent instances created from roles, recipes, explicit launch profiles, or specialists. The canonical lifecycle skill for general live-agent work after any specialist-scoped launch or stop entry. | `houmao-mgr agents launch|join|list|stop|relaunch|cleanup` |

### Agent inspection, communication, gateway, and mailbox

| Skill | What it enables | Canonical CLI routing |
|---|---|---|
| `houmao-agent-inspect` | Generic read-only inspection of Houmao-managed agents: target discovery, liveness, screen posture, mailbox posture, runtime artifacts, logs, durable headless turn evidence, and bounded local tmux peeking when higher-level surfaces are insufficient. | `houmao-mgr agents list|state`, `houmao-mgr agents gateway status|tui state|history|watch`, `houmao-mgr agents mail resolve-live|status|check`, `houmao-mgr agents mailbox status`, `houmao-mgr agents turn status|events|stdout|stderr` |
| `houmao-agent-messaging` | Communicate with already-running managed agents — synchronous prompt and interrupt, queued gateway requests, raw `send-keys`, mailbox routing, reset-context guidance, and request-scoped headless execution overrides through `--model` plus optional `--reasoning-level`. Routes by **communication intent**, not by one hardcoded transport. Prefers live gateway-backed delivery when available. | `houmao-mgr agents prompt|interrupt`, `houmao-mgr agents gateway prompt|interrupt|send-keys|tui state|history|note-prompt`, `houmao-mgr agents turn submit`, `houmao-mgr agents mail resolve-live` |
| `houmao-agent-gateway` | Live gateway lifecycle, manifest-first discovery from inside or outside the attached session, gateway-only control surfaces, ranked direct reminders, and gateway mail-notifier behavior. Distinct from `houmao-agent-messaging` because it focuses on the gateway sidecar itself, not the messages going through it. | `houmao-mgr agents gateway attach|detach|status|tui watch`, `houmao-mgr agents gateway mail-notifier status|enable|disable` |
| `houmao-mailbox-mgr` | Mailbox administration for filesystem mailbox roots, project mailbox roots, structural mailbox inspection, and late filesystem mailbox binding on existing local managed agents. This is the mailbox-admin skill, not the ordinary mailbox-participation skill. | `houmao-mgr mailbox ...`, `houmao-mgr project mailbox ...`, `houmao-mgr agents mailbox ...` |
| `houmao-agent-email-comms` | Unified ordinary shared-mailbox operations and no-gateway fallback guidance. Covers gateway-backed `/v1/mail/*` work, transport-local context, and the no-gateway fallback path. The canonical mailbox-operations skill paired with `houmao-mgr agents mail`. | `houmao-mgr agents mail status|check|send|reply|mark-read|resolve-live` |
| `houmao-process-emails-via-gateway` | Round-oriented workflow for processing notifier-driven unread shared-mailbox emails through a prompt-provided gateway base URL: gateway-API-first triage, selective inspection, post-success mark-read, and stop-after-round discipline. | `houmao-mgr agents mail check|mark-read` plus the live gateway `/v1/mail/*` facade |
| `houmao-adv-usage-pattern` | Supported advanced mailbox and gateway workflow compositions layered on top of the direct-operation skills, starting with self-wakeup through self-mail plus notifier-driven rounds. | The composed `houmao-mgr agents mail ...` and `houmao-mgr agents gateway ...` families, plus the live gateway `/v1/mail/*` facade through the direct-operation skills |

### Loop authoring and master-run control

| Skill | What it enables | Canonical CLI routing |
|---|---|---|
| `houmao-agent-loop-pairwise` | Restore the stable pairwise surface: author a master-owned pairwise loop plan from user intent, render the final Mermaid control graph, and operate the accepted run through `start`, `status`, and `stop`. Keeps the user agent outside the execution loop while leaving prestart and expanded operator verbs to the versioned enriched skill. | Routes through `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, and `houmao-adv-usage-pattern` for execution; the skill itself is authoring plus `start|status|stop` control |
| `houmao-agent-loop-pairwise-v2` | Preserve the enriched versioned pairwise workflow: author a master-owned pairwise loop plan from user intent, run canonical `initialize`, render the final Mermaid control graph, and operate the accepted run through `start`, `peek`, `ping`, `pause`, `resume`, `stop`, and `hard-kill`. Keeps the user agent outside the execution loop, separates observed states from operator actions, and routes optional overdue downstream peeking through `houmao-agent-inspect`. | Routes through `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, `houmao-mailbox-mgr`, `houmao-agent-inspect`, and `houmao-adv-usage-pattern` for execution; the skill itself is authoring plus `plan|initialize|start|peek|ping|pause|resume|stop|hard-kill` control |
| `houmao-agent-loop-relay` | Author a master-owned relay loop plan from user intent, render the final Mermaid relay graph, and operate the accepted run through `start`, `status`, and `stop`. Normalizes forwarding authority explicitly, evaluates completion centrally at the origin, and returns the final result to the designated origin rather than cycling through worker-to-worker hand-offs. | Routes through `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, and `houmao-adv-usage-pattern` for execution; the skill itself is authoring plus `start|status|stop` control |

## Auto-Install vs Explicit Install

The same catalog can land in a tool home through either path, but the **default selections** are different.

```
                       INSTALL DEFAULTS
                ════════════════════════════════════

   Managed launch / join                Explicit external install
   (auto, into managed home)            (houmao-mgr system-skills install
                                         --tool <t> --home <path>)
   ┌───────────────────────────┐        ┌───────────────────────────┐
   │ mailbox-full              │        │ mailbox-full              │
   │ advanced-usage            │        │ advanced-usage            │
   │ touring                   │        │ touring                   │
   │ user-control              │        │ user-control              │
   │ agent-inspect            │        │ agent-inspect            │
   │ agent-messaging           │        │ agent-instance  ◄── ADDS  │
   │ agent-gateway             │        │ agent-messaging           │
   │                           │        │ agent-gateway             │
   │ → every catalog skill     │        │                           │
   │    except the lifecycle-  │        │ → every catalog skill,    │
   │    only agent-instance:   │        │    including              │
   │  process-emails-via-gw    │        │    agent-instance:        │
   │  agent-email-comms        │        │  all of managed launch    │
   │  mailbox-mgr              │        │  PLUS:                    │
   │  adv-usage-pattern        │        │  agent-instance           │
   │  touring                  │        │                           │
   │  project-mgr              │        │                           │
   │  specialist-mgr           │        │                           │
   │  credential-mgr           │        │                           │
   │  agent-definition         │        │                           │
   │  agent-loop-pairwise      │        │                           │
   │  agent-loop-pairwise-v2   │        │                           │
   │  agent-loop-relay         │        │                           │
   │  agent-inspect            │        │                           │
   │  agent-messaging          │        │                           │
   │  agent-gateway            │        │                           │
   └───────────────────────────┘        └───────────────────────────┘
```

The exact counts follow the resolved `catalog.toml` sets, so the "managed launch / join" column grows whenever a new skill joins `user-control`, `mailbox-full`, `advanced-usage`, `touring`, `agent-inspect`, `agent-messaging`, or `agent-gateway`, and the "explicit external install" column grows the same way plus `agent-instance`.

The catalog source of truth lives at `src/houmao/agents/assets/system_skills/catalog.toml`:

```toml
[auto_install]
managed_launch_sets = ["mailbox-full", "advanced-usage", "touring", "user-control", "agent-inspect", "agent-messaging", "agent-gateway"]
managed_join_sets   = ["mailbox-full", "advanced-usage", "touring", "user-control", "agent-inspect", "agent-messaging", "agent-gateway"]
cli_default_sets    = ["mailbox-full", "advanced-usage", "touring", "user-control", "agent-instance", "agent-inspect", "agent-messaging", "agent-gateway"]
```

The named sets resolve as:

| Set | Skills it expands to |
|---|---|
| `mailbox-core` | `houmao-process-emails-via-gateway`, `houmao-agent-email-comms` |
| `mailbox-full` | `houmao-process-emails-via-gateway`, `houmao-agent-email-comms`, `houmao-mailbox-mgr` |
| `advanced-usage` | `houmao-adv-usage-pattern` |
| `touring` | `houmao-touring` |
| `user-control` | `houmao-project-mgr`, `houmao-specialist-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-relay` |
| `agent-instance` | `houmao-agent-instance` |
| `agent-inspect` | `houmao-agent-inspect` |
| `agent-messaging` | `houmao-agent-messaging` |
| `agent-gateway` | `houmao-agent-gateway` |

### Why managed launch/join leaves out `houmao-agent-instance`

When the operator launches or joins through `houmao-mgr`, **the operator already has full instance lifecycle control**. The packaged `houmao-agent-instance` skill exists for the case where an agent in some other managed home needs to drive lifecycle for live agents itself. Inside a freshly-managed home there is no second-tier instance authority to delegate to, so the auto-install set keeps the lifecycle-only skill out and lets `system-skills install` add it on demand for external homes that want the full agent-driven surface.

### How to install the broader CLI-default set

To prepare an external tool home (one that did not come from a `houmao-mgr agents launch` or `agents join` flow) with the full CLI-default selection — every catalog skill including the lifecycle-only `houmao-agent-instance` — omit both `--set` and `--skill`:

```bash
houmao-mgr system-skills install --tool claude --home ~/.claude
```

When `--home` is omitted, the effective home resolves through `--home` → tool-native env var (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `GEMINI_CLI_HOME`) → project-scoped default (`<cwd>/.claude`, `<cwd>/.codex`, `<cwd>` for Gemini). The default Gemini root is the project cwd because Gemini's own state lives under `<cwd>/.gemini/`; omitted-home Gemini installs land under `<cwd>/.gemini/skills/`.

For named-set or explicit-skill installs, repeat `--set <name>` or `--skill <name>` selectors. Add `--symlink` to install selected skills as directory symlinks to the packaged asset roots instead of copied trees — useful for development homes where you want the installed skill to track changes in the source tree.

For the full flag surface, see the [`system-skills` CLI reference](../reference/cli/system-skills.md).

## When to Use Which Skill

Two short heuristics help decide which skill applies to a task that an agent or operator is asked to perform:

**By entry style.** When the user explicitly asks for a first-run guided tour or wants help re-orienting from current Houmao state, start with `houmao-touring`. It is the manual guided entrypoint that inspects current posture, explains the next likely branches, and routes execution to the maintained Houmao-owned skills rather than flattening them into one broad direct-operation surface.

**By concern.** Project overlay lifecycle, `.houmao/` layout, project-aware side effects, explicit launch profiles, and project-scoped easy-instance inspection belong to `houmao-project-mgr`. Authoring and inspecting *what an agent is* — its specialist, credentials, role, recipe — belongs to `houmao-specialist-mgr`, `houmao-credential-mgr`, or `houmao-agent-definition`. Inspecting *what one live managed agent is doing right now* — liveness, screen posture, mailbox posture, logs, artifacts, or tmux backing — belongs to `houmao-agent-inspect`. Administering *mailbox authority itself* — mailbox roots, mailbox registrations, and late mailbox binding — belongs to `houmao-mailbox-mgr`. Driving *what a live agent does* — sending it a prompt, attaching a gateway, or participating in mailbox workflows — belongs to `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, or `houmao-process-emails-via-gateway`.

**By transport and boundary.** When the task is "inspect this running agent," start with `houmao-agent-inspect` and let it choose summary state, managed detail, gateway TUI tracking, mailbox posture, logs, artifacts, or tmux peek in that order. When the task is "communicate with this running agent," start with `houmao-agent-messaging` and let it route by intent. When the task is "do something to the gateway sidecar itself" (attach, detach, watch its TUI tracker, change its mail-notifier polling), use `houmao-agent-gateway`. When the task is "manage mailbox roots, mailbox registrations, or late mailbox binding," use `houmao-mailbox-mgr`. When the task is "handle ordinary mail," use `houmao-agent-email-comms`. When the task is "process the unread mail batch the notifier just told us about," use the round-oriented `houmao-process-emails-via-gateway`. When the task is "use a supported multi-skill mailbox or gateway composition such as self-wakeup through self-mail," use `houmao-adv-usage-pattern`. When the task is "what project is active here?" or "what changes for other subcommands when `.houmao/` exists?", use `houmao-project-mgr`.

## See Also

- [`system-skills` CLI reference](../reference/cli/system-skills.md) — full flag surface, effective-home resolution, and projection paths.
- [Easy Specialists guide](easy-specialists.md) — the operator-facing flow that exercises `houmao-specialist-mgr`.
- [Launch Profiles guide](launch-profiles.md) — the launch-side concepts that the messaging and gateway skills observe.
- [Agent Definition Directory](agent-definitions.md) — `.houmao/` layout, catalog-versus-projection storage, and project-local authoring paths.
- [Project-Aware Operations](../reference/system-files/project-aware-operations.md) — project-aware root resolution and affected command families.
- README "System Skills" subsection — the catalog-table view bridging this narrative to the per-skill rows.
