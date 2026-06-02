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

Every current packaged Houmao system skill supports explicit skill-level help from its top-level `SKILL.md`. Ask the agent for `$houmao-touring help`, `$houmao-agent-email-comms help`, or "usage for `houmao-agent-definition`" when you want a read-only summary before starting a workflow. Help responses state the skill purpose, available functionality, common starting prompts, and related skill boundaries; they do not run commands, mutate files, send mail, change gateway state, or change managed-agent lifecycle state.

The help trigger is intentionally narrow. Explicit help or usage requests are handled before normal workflow routing, action-page routing, branch selection, transport selection, or missing-input collection. Ordinary task requests such as "help me send mail to this agent" or "help me launch this profile" still route to the task workflow instead of stopping at generic usage text.

## Installation Choices

When `npx` is available and the target machine has internet access, the recommended user-driven install path is the external Skills CLI pointed at Houmao's namespace in the small release-synced `igamenovoer/tool-skills` repository:

```bash
npx skills add igamenovoer/tool-skills/houmao
```

That command points at `tool-skills/houmao`, not at the full Houmao source repository, so the clone is small and the user can choose which packaged skill or skills to install. The mirror is updated from Houmao releases.

Use Houmao's own installer when `npx` is unavailable, when working offline from an installed Houmao package, or when the install needs Houmao-specific projection behavior such as named sets, subset skills, explicit homes, symlink/copy projection, or retired-skill cleanup:

```bash
houmao-mgr system-skills install --tool claude,codex,copilot,gemini
houmao-mgr system-skills install --tool codex --skill-set core
houmao-mgr system-skills install --tool codex --home ~/.codex --skill houmao-agent-definition --symlink
```

Managed launch and join are separate from these explicit user-driven installation choices. `agents join` still auto-installs the catalog's `core` set into adopted managed homes. Managed launch defaults to the same `core` selection, but specialists, recipes, and launch profiles can now store a managed system-skill policy that extends, replaces, or disables that selection for future managed homes. Omitted-selection `houmao-mgr system-skills install` remains the explicit external/project-home installer and uses the catalog's `all` set.

## The Packaged Skills

Houmao currently ships the set of system skills declared in `src/houmao/agents/assets/system_skills/catalog.toml`. They split into three organization groups: **automation** for autonomous agent operation, mailbox/gateway/memory behavior, messaging, and inspection; **control** for operator-facing project, specialist, credential, definition, lifecycle, touring, and loop workflows; and **utils** for optional utility workflows.

### Control: Guided Touring

| Skill | What it enables | Canonical CLI routing |
|---|---|---|
| `houmao-touring` | Manual guided tour for first-time or re-orienting users. It starts from current state and teaches Houmao in stages: beginner agent creation and first conversation, intermediate memo/mailbox/gateway/inspection workflows, and advanced loop or isolated workspace coordination when relevant. Use it only when the user explicitly asks for the tour. | Routes through the maintained `houmao-mgr project ...`, `houmao-mgr project mailbox ...`, `houmao-mgr project ...`, `houmao-mgr agents ...`, loop, workspace, and direct-operation skill families via the dedicated Houmao-owned skills |

### Control: Project, agent definition, and credential authoring

| Skill | What it enables | Canonical CLI routing |
|---|---|---|
| `houmao-project-mgr` | Project overlay lifecycle, `.houmao/` layout explanation, project-aware command-effect guidance, and project-scoped easy-instance inspection or stop routing. | `houmao-mgr project init`, `houmao-mgr project status`, `houmao-mgr project agents list|get|stop` |
| `houmao-agent-definition` | Canonical pre-launch agent-definition workflows through subcommands: `roles`, `recipes`, `launch-dossiers`, `specialists`, `profiles`, `create-agent-fast-forward`, `launch-agent`, and `stop-agent`. Loose profile wording defaults to `profiles`; use `launch-dossiers` only for raw, recipe-backed, or exact `internals native-agent launch-dossiers` requests. | `houmao-mgr internals native-agent roles ...`, `houmao-mgr internals native-agent recipes ...`, `houmao-mgr internals native-agent launch-dossiers ...`, `houmao-mgr project specialist ...`, `houmao-mgr project profile ...`, `houmao-mgr project agents launch|stop` |
| `houmao-specialist-mgr` | Compatibility wrapper for older prompts and installed homes. It redirects specialist, profile, old ready-profile, easy launch, or easy stop requests to `houmao-agent-definition` subcommands. | No independent command ownership |
| `houmao-credential-mgr` | Add, update, inspect, rename, and remove credentials for Claude, Codex, and Gemini in either a selected Houmao project or a direct native-agent root. Manages credential contents and names, not stored profile-level auth overrides. | `houmao-mgr project [--project-dir <dir>] credentials <tool> list|get|add|set|rename|remove` / `houmao-mgr internals native-agent credentials <tool> ... --native-agent-root <path>` |

### Control: Agent definition and instance management

| Skill | What it enables | Canonical CLI routing |
|---|---|---|
| `houmao-agent-instance` | Launch, adopt (`join`), list, stop, relaunch, and clean up live managed-agent instances created from roles, recipes, launch dossiers, or specialists. The canonical lifecycle skill for general live-agent work after any specialist-scoped launch or stop entry. | `houmao-mgr agents launch|join|list|stop|relaunch|cleanup` |

### Automation

| Skill | What it enables | Canonical CLI routing |
|---|---|---|
| `houmao-agent-inspect` | Generic read-only inspection of Houmao-managed agents: target discovery, liveness, screen posture, mailbox posture, runtime artifacts, logs, durable headless turn evidence, and bounded local tmux peeking when higher-level surfaces are insufficient. | `houmao-mgr agents list|state`, `houmao-mgr agents gateway status|tui state|history|watch`, `houmao-mgr agents mail resolve-live|status|list`, `houmao-mgr agents mailbox status`, `houmao-mgr agents turn status|events|stdout|stderr` |
| `houmao-operator-messaging` | Manual operator messaging layer for clarifying operator intent, selecting one or more managed-agent targets, dispatching by prompt by default, and using mailbox only when the operator asks for mail-style delivery. Use it only when the operator explicitly selects this clarification/dispatch surface. | Routes prompt packets through `houmao-agent-messaging` and mailbox packets through `houmao-agent-email-comms`; recommends loop skills for durable orchestration |
| `houmao-agent-messaging` | Communicate with already-running managed agents — synchronous prompt and interrupt, queued gateway requests, raw `send-keys`, mailbox routing, reset-context guidance, and request-scoped headless execution overrides through `--model` plus optional `--reasoning-level`. Routes by **communication intent**, not by one hardcoded transport. Prefers live gateway-backed delivery when available. | `houmao-mgr agents prompt|interrupt`, `houmao-mgr agents gateway prompt|interrupt|send-keys|tui state|history|note-prompt`, `houmao-mgr agents turn submit`, `houmao-mgr agents mail resolve-live` |
| `houmao-agent-gateway` | Live gateway lifecycle, manifest-first discovery from inside or outside the attached session, gateway-only control surfaces, ranked direct reminders, and gateway mail-notifier behavior. Distinct from `houmao-agent-messaging` because it focuses on the gateway sidecar itself, not the messages going through it. | `houmao-mgr agents gateway attach|detach|status|tui watch`, `houmao-mgr agents gateway mail-notifier status|enable|disable` |
| `houmao-mailbox-mgr` | Mailbox administration for filesystem mailbox roots, project mailbox roots, structural mailbox inspection, and late filesystem mailbox binding on existing local managed agents. This is the mailbox-admin skill, not the ordinary mailbox-participation skill. | `houmao-mgr mailbox ...`, `houmao-mgr project mailbox ...`, `houmao-mgr agents mailbox ...` |
| `houmao-memory-mgr` | Managed-agent memory work: reading, editing, appending, pruning, and organizing the fixed `houmao-memo.md` file and contained `pages/` files while preserving authored memo links across relaunch, reset, and `recover_and_continue` flows. | `houmao-mgr agents memory path|status`, `houmao-mgr agents memory memo show|set|append`, `houmao-mgr agents memory tree|resolve|read|write|append|delete` |
| `houmao-agent-email-comms` | Unified ordinary shared-mailbox operations and no-gateway fallback guidance. Covers gateway-backed `/v1/mail/*` work, transport-local context, and the no-gateway fallback path. The canonical mailbox-operations skill paired with `houmao-mgr agents mail`. | `houmao-mgr agents mail resolve-live|status|list|peek|read|send|post|reply|mark|move|archive` |
| `houmao-process-emails-via-gateway` | Round-oriented workflow for processing notifier-driven shared-mailbox emails through a prompt-provided gateway base URL: gateway-API-first triage, selective inspection, post-success archive, and stop-after-round discipline. | `houmao-mgr agents mail list|peek|read|reply|archive` plus the live gateway `/v1/mail/*` facade |
| `houmao-adv-usage-pattern` | Supported advanced mailbox and gateway workflow compositions layered on top of the direct-operation skills, starting with self-wakeup through self-mail plus notifier-driven rounds. | The composed `houmao-mgr agents mail ...` and `houmao-mgr agents gateway ...` families, plus the live gateway `/v1/mail/*` facade through the direct-operation skills |

### Utils

| Skill | What it enables | Canonical CLI routing |
|---|---|---|
| `houmao-utils-llm-wiki` | Persistent Markdown LLM Wiki knowledge-base workflows: scaffold, ingest, compile, query, lint, audit, and local viewer launch. This is a utility skill, not a managed-agent lifecycle or messaging control surface. | Installed through `houmao-mgr system-skills install --tool <tool> --skill-set all` or `--skill houmao-utils-llm-wiki`; inside the skill, helper workflows use `python3 scripts/...` from the installed skill root |
| `houmao-utils-workspace-mgr` | Multi-agent workspace planning, creation, validation, and summarization: dry-run plans, untracked task-scoped in-repo workspace collections, out-of-repo standard workspace layouts, per-agent Git worktrees, local-only shared repos, safe local-state symlinks, tracked submodule materialization, launch-profile cwd updates, project-command readiness checks, and optional memo-seed workspace rules. This is a utility skill, not a managed-agent lifecycle or messaging control surface. | Installed through `houmao-mgr system-skills install --tool <tool> --skill-set all` or `--skill houmao-utils-workspace-mgr`; it prepares and validates Houmao-standard workspace structure before agents are launched |

### Control: Loop authoring and master-run control

| Skill | What it enables | Canonical CLI routing |
|---|---|---|
| `houmao-agent-loop-lite` | Pro-shaped routed loop authoring and generated-loop execution surface with lightweight artifacts. It keeps the `intention/`, `execplan/`, and `runs/` spine while using Markdown contracts, typed Markdown templates, required generated skills, and direct SQLite state instead of generated harness or docs layers. | Routes platform operations through `houmao-agent-definition`, `houmao-utils-workspace-mgr`, `houmao-agent-instance`, `houmao-agent-email-comms`, `houmao-agent-gateway`, `houmao-agent-inspect`, and related maintained skills; generated loop behavior lives in loop-local Markdown contracts and generated skills |
| `houmao-agent-loop-pro` | Schema-rich loop authoring and generated-loop execution surface. It scaffolds intention material, clarifies intent, generates execplans in `tree-loop` and `generic-loop` topology modes, validates artifacts, prepares agents/workspaces, launches agents, and operates generated loops through loop-specific operator controls. | Routes platform operations through `houmao-agent-definition`, `houmao-utils-workspace-mgr`, `houmao-agent-instance`, `houmao-agent-email-comms`, `houmao-agent-gateway`, `houmao-agent-inspect`, and related maintained skills; generated loop behavior lives in the loop-local execplan artifacts |

### Graph Tooling for Loop Authoring

When authoring or validating topology-heavy generated artifacts with `houmao-agent-loop-pro`, the `houmao-mgr internals graph high` commands provide deterministic structural helpers that can be called from inside an agent session:

| Command | What it provides |
|---|---|
| `graph high analyze` | Root reachability, leaves, delegating participants, cycle/DAG posture, shape warnings |
| `graph high packet-expectations` | Expected routing-packet structure derived from graph topology when the generated execplan uses packet-style routing |
| `graph high validate-packets` | Validation errors for a routing-packet document against graph-derived expectations |
| `graph high slice` | Ancestor, descendant, reachable, or component subgraph extraction |
| `graph high render-mermaid` | Deterministic Mermaid scaffolding from graph structure |

All commands accept NetworkX node-link JSON via `--input` and emit structured results or node-link JSON. For the full option reference, see [internals graph](../reference/cli/internals.md).

## Auto-Install vs Explicit Install

The catalog exposes two installable sets so internal skill routing does not point at missing skills:

| Install path | Set | Meaning |
|---|---|---|
| Managed launch / join | `core` | The closed automation and control surface for managed agents |
| CLI default | `all` | `core` plus the utility skills |

The skills are still organized conceptually into three groups. Automation covers mailbox rounds, direct mailbox operations, managed memory, advanced workflow patterns, read-only inspection, operator messaging, managed-agent messaging, and gateway/reminder control. Control covers touring, project overlays, agent definitions and profiles, credentials, live-agent lifecycle, and loop orchestration. Utils covers `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr`.

The catalog source of truth lives at `src/houmao/agents/assets/system_skills/catalog.toml`:

```toml
[auto_install]
managed_launch_sets = ["core"]
managed_join_sets   = ["core"]
cli_default_sets    = ["all"]
```

The named sets resolve as:

| Set | Skills it expands to |
|---|---|
| `core` | All non-utility packaged skills: automation plus operator-control skills |
| `all` | `core` plus `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr` |

Managed launch stores policy separately from explicit `system-skills install`. A source recipe or specialist may record:

```yaml
launch:
  system_skills:
    mode: extend
    skills:
      - houmao-utils-llm-wiki
```

Source policies use `default`, `extend`, `replace`, or `none`; omitted source policy is `default`, which expands the catalog's `managed_launch_sets`. Launch profiles use `inherit`, `extend`, `replace`, or `none`; omitted profile policy is `inherit`, which uses the source's effective selection. On reused managed homes, the managed-home sync removes exact catalog-known Houmao system-skill paths that are no longer selected while preserving unrelated user skill paths.

### How to install the CLI-default set

To prepare an external tool home with the CLI-default selection, omit both `--skill-set` and `--skill`, or pass `--skill-set all` explicitly:

```bash
houmao-mgr system-skills install --tool claude,codex,copilot,gemini
houmao-mgr system-skills install --tool claude --home ~/.claude
houmao-mgr system-skills install --tool copilot
houmao-mgr system-skills install --tool copilot --home ~/.copilot
```

When `--home` is omitted, the effective home resolves through tool-native env var (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `COPILOT_HOME`, `GEMINI_CLI_HOME`) → project-scoped default (`<cwd>/.claude`, `<cwd>/.codex`, `<cwd>/.github` for Copilot, `<cwd>` for Gemini). Comma-separated multi-tool installs must omit `--home` so each selected tool resolves independently. The default Gemini root is the project cwd because Gemini's own state lives under `<cwd>/.gemini/`; omitted-home Gemini installs land under `<cwd>/.gemini/skills/`. The default Copilot home is `<cwd>/.github`, so omitted-home Copilot installs land under `<cwd>/.github/skills/`. Use a single-tool command with `--home ~/.copilot` when you want a personal Copilot CLI skill install instead of a repository-local Copilot skill install.

Copilot repository skills can be discovered by Copilot surfaces that read `.github/skills/`, but discovery is not the same as runtime reachability. The Houmao system skills still route to `houmao-mgr` and often inspect or mutate local project, tmux, gateway, mailbox, and managed-agent resources; those operations require a local or otherwise provisioned environment where those resources are available.

For named-set or explicit-skill installs, repeat `--skill-set <name>` or `--skill <name>` selectors. Add `--symlink` to install selected skills as directory symlinks to the packaged asset roots instead of copied trees — useful for development homes where you want the installed skill to track changes in the source tree.

Use `--skill-set core` when the target home should avoid utility workflows. On a home that already has `core`, install one utility by explicit skill name when you do not want the rest of `all`:

```bash
houmao-mgr system-skills install --tool codex --skill-set core
houmao-mgr system-skills install --tool codex --skill houmao-utils-llm-wiki
houmao-mgr system-skills install --tool codex --skill houmao-utils-workspace-mgr
```

### How to remove installed system skills

To remove Houmao-owned system skills from an external or project-scoped tool home, use `system-skills uninstall`:

```bash
houmao-mgr system-skills uninstall --tool codex
houmao-mgr system-skills uninstall --tool codex --home ~/.codex
houmao-mgr system-skills uninstall --tool claude,codex,copilot,gemini
```

Uninstall intentionally does **not** mirror install selection. It removes all current catalog-known Houmao system-skill paths for the resolved tool home, whether those paths are copied directories, symlinks, or files. It leaves parent skill roots, unrelated user skills, legacy family-namespaced paths, unrecognized `houmao-*` paths, and obsolete install-state files in place.

For the full flag surface, see the [`system-skills` CLI reference](../reference/cli/system-skills.md).

## When to Use Which Skill

Two short heuristics help decide which skill applies to a task that an agent or operator is asked to perform:

**By entry style.** When the user explicitly asks for a first-run guided tour or wants help re-orienting from current Houmao state, start with `houmao-touring`. It is the manual guided entrypoint that inspects current posture, offers stage-aware next actions, and teaches beginner setup, intermediate live operation, and advanced coordination rather than flattening every function into one broad reference surface.

**By concern.** Project overlay lifecycle, `.houmao/` layout, project-aware side effects, and project-scoped easy-instance inspection belong to `houmao-project-mgr`. Authoring and inspecting *what an agent is before launch* belongs to `houmao-agent-definition`: use `roles`, `recipes`, `launch-dossiers`, `specialists`, `profiles`, or `create-agent-fast-forward`. Ordinary profile wording means `profiles`; `launch-dossiers` is the explicit recipe-backed low-level route. Credential bundle contents belong to `houmao-credential-mgr`. Inspecting *what one live managed agent is doing right now* - liveness, screen posture, mailbox posture, logs, artifacts, or tmux backing - belongs to `houmao-agent-inspect`. Editing the per-agent `houmao-memo.md` file or contained `pages/` files belongs to `houmao-memory-mgr`. Building or maintaining a persistent Markdown knowledge base belongs to `houmao-utils-llm-wiki`. Planning, creating, validating, or summarizing a multi-agent workspace before launch belongs to `houmao-utils-workspace-mgr`. Administering *mailbox authority itself* - mailbox roots, mailbox registrations, and late mailbox binding - belongs to `houmao-mailbox-mgr`. Clarifying operator intent and dispatching one or more prompt-by-default or mailbox-on-request packets belongs to `houmao-operator-messaging`. Driving *what a live agent does* - sending it a prompt, attaching a gateway, or participating in mailbox workflows - belongs to `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, or `houmao-process-emails-via-gateway`. Lightweight Markdown/direct-SQL loop packages belong to `houmao-agent-loop-lite`; topology-rich schema/harness loop packages belong to `houmao-agent-loop-pro`.

**By transport and boundary.** When the task is "inspect this running agent," start with `houmao-agent-inspect` and let it choose summary state, managed detail, gateway TUI tracking, mailbox posture, logs, artifacts, or tmux peek in that order. When the task is "edit this agent's memo" or "add/remove something from the agent memo," use `houmao-memory-mgr`. When the task is "clarify this operator instruction and dispatch it to agents," use `houmao-operator-messaging`. When the task is "communicate with this running agent," start with `houmao-agent-messaging` and let it route by intent. When the task is "do something to the gateway sidecar itself" (attach, detach, watch its TUI tracker, change its mail-notifier polling), use `houmao-agent-gateway`. When the task is "manage mailbox roots, mailbox registrations, or late mailbox binding," use `houmao-mailbox-mgr`. When the task is "handle ordinary mail," use `houmao-agent-email-comms`. When the task is "process the mailbox work the notifier just reported," use the round-oriented `houmao-process-emails-via-gateway`. When the task is "use a supported multi-skill mailbox or gateway composition such as self-wakeup through self-mail," use `houmao-adv-usage-pattern`. When the task is "what project is active here?" or "what changes for other subcommands when `.houmao/` exists?", use `houmao-project-mgr`.

## See Also

- [`system-skills` CLI reference](../reference/cli/system-skills.md) — full flag surface, effective-home resolution, and projection paths.
- [Easy Specialists guide](easy-specialists.md) — the operator-facing flow whose agent-facing guidance now lives under `houmao-agent-definition`.
- [Launch Profiles guide](launch-profiles.md) — the launch-side concepts that the messaging and gateway skills observe.
- [Agent Definition Directory](agent-definitions.md) — `.houmao/` layout, catalog-versus-projection storage, and project-local authoring paths.
- [Project-Aware Operations](../reference/system-files/project-aware-operations.md) — project-aware root resolution and affected command families.
- README "System Skills" subsection — the catalog-table view bridging this narrative to the per-skill rows.
