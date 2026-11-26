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

# Concepts

Use this self-contained reference to ground Houmao vocabulary during `houmao-admin-welcome`. Route concrete operator actions through `$houmao-admin-entrypoint <route> ...` (or `$houmao-shared-routines <route> ...` for advanced direct use) rather than presenting shared children as standalone skills. Operators can also read packaged CLI guides directly via `houmao-mgr manual`.

## Project, Skills, and Definitions

- **Project overlay (`.houmao/`)**: project-local directory holding `catalog.sqlite`, `content/` (including canonical `project skills` under `.houmao/content/skills/`), `agents/`, credentials, mailbox, and memory; upgradable in place with `houmao-mgr project migrate [--apply]`. Owning routine: `houmao-project-mgr`.
- **System-skill packs**: static packaged skill sets (`admin` and `agent`) installed or diagnosed via `houmao-mgr system-skills {list|install|status|doctor|upgrade|uninstall}`, distinct from user-authored `project skills`.
- **Tool adapter and run modes**: per-tool runtime contract across four adapters and qualified run modes: `claude` (`headless`, `tui`), `codex` (`headless`, `service`, `tui`), `kimi` (`headless`, `service`, `tui`, `web`), and `dsh` / DeepSeek Harness (`headless`, `service`, `web`), configurable with layered `tool_params`. Owning routines: `houmao-agent-definition`, `houmao-credential-mgr`.
- **Recipe and launch dossier**: low-level build bundle (role prompt, tool adapter, skills, auth) and reusable birth-time launch profile (identity, workdir, prompt mode, env, mailbox, gateway, `managed_header` v2). Owning routine: `houmao-agent-definition`.
- **Specialist and project profile**: reusable high-level agent template (role + tool + credential) and optional birth-time default wrapper layered on a specialist. Owning routine: `houmao-agent-definition`.
- **Agent Definition Revision and Deployment**: immutable portable definition package (`definition-authoring`) and durable project binding (`definition-deployment`, `definition-batch`) that resolves deploy inputs into launch-ready contracts without auto-launching. Owning routine: `houmao-agent-definition`.

## Runtime, Executors, Inspection, and Memory

- **Managed agent and execution binding (`--executor`)**: a supervised Houmao instance running locally or in an explicit execution-owner context (`--executor`), with operator locators maintained via `houmao-mgr admin executors {reconcile|forget}`. Lifecycle verbs (`launch`, `relaunch`, `stop`, `cleanup`) stay distinct; Kimi Web owners can open a local browser via `agents single ... open-browser`. Owning routine: `houmao-agent-instance`.
- **External agent (`agents external`)**: a local communication-only import (`register`, `list`, `get`, `verify`, `remove`) pointing at a remotely owned agent on `houmao-passive-server` without transferring lifecycle ownership. Owning routines: `houmao-agent-instance`, `houmao-agent-inspect`.
- **Runtime variables and named mindsets**: revisioned per-instance non-secret values (`runtime-variables`) and atomic question-set snapshots (`mindsets`). Owning routine: `houmao-agent-instance`.
- **Durable usage records**: per-turn token and cost accounting persisted in `<session-root>/usage/records.sqlite3` (`usage-start.json`, `usage-final.json`) and exposed read-only at `GET /v1/usage` and `GET /houmao/agents/{agent_ref}/usage`. Owning routine: `houmao-agent-inspect`.
- **Managed-agent memo and pages**: live `houmao-memo.md` (surfaced via `MANAGED_PROMPT_HEADER_VERSION = 2` `<memo_cue>`) and structured `pages/` entries, kept separate from birth-time profile memo seeds. Owning routine: `houmao-memory-mgr`.

## Gateway, Access, Files, Mail, and CCCC

- **Gateway sidecar and public dashboard**: per-agent HTTP sidecar (foreground auxiliary tmux window by default, `--background` opt-in, `60s` single-use `web-entry`) serving live control routes plus `GET /` and `/v1/endpoint` (`admin_mode: open|keyed|unavailable`). Owning routine: `houmao-agent-gateway`.
- **Gateway access policy and built-in groups**: retained and live authorization (`agent-observer`, `agent-requester`, `agent-maintainer`, `agent-operator`, `agent-admin`, plus `managed-self`), `default-group`, enrolled SSH keys, `self-key {rotate|revoke}`, and exact-resource role templates. Open-roster gateways accept unauthenticated local setup until admin keys enroll (`keyed`). Owning routine: `houmao-agent-access`.
- **Attributed `request` vs direct `prompt`**: `agents single ... request` submits an attributed task under `agent-requester` default authority, whereas `prompt` injects a verbatim turn requiring `agent-operator` authority. Owning routines: `houmao-agent-messaging`, `houmao-operator-messaging`.
- **Versioned logical mounts (`skills`, `mcp`)**: lease-backed draft, commit, `publish` (including `agents self files push --when-idle` on qualified DSH Web targets), and `reconcile` workflows over gateway-hosted files. Owning routine: `houmao-agent-files`.
- **Offline and Stalwart online mail**: independent `offline` (filesystem/project root, `<agentname>@houmao.localhost`, `HOUMAO-*` system principal reserve) and `online` (`agents single|self mailbox online` JMAP attachment to Stalwart with `Inbox`/`Sent`/`Archive` roles) slots. Administration belongs to `houmao-mailbox-mgr`; ordinary mail belongs to `houmao-agent-email-comms`; bounded notifier rounds belong to `houmao-process-emails-via-gateway`.
- **`houmao-cccc` plugin and CLI**: optional gateway plugin (`/v1/plugins/{instance}/*`, `--plugin-config-override`) and `houmao-cccc` CLI supporting group discovery, connection tokens, and push/pull/queue `chat` and `mail` delivery, distinct from native Houmao `prompt` and `/v1/mail/*`. Owning routines: `houmao-agent-gateway`, `houmao-agent-messaging`, `houmao-adv-usage-pattern`.

## Workspaces, Loops, and AG-UI

- **Multi-agent vs Private Workspace**: `houmao-utils-workspace-mgr` plans and validates multi-agent Git worktrees and `--executor`/DSH Web workdirs; `houmao-shared-routines->houmao-agent-instance->private-workspace()` manages an individual agent's TOML/SQLite auxiliary workspace.
- **Adv usage patterns vs Lite/Pro loops**: `houmao-adv-usage-pattern` covers lightweight wakeup, notifier, pairwise, relay, and `houmao-cccc` coordination; `houmao-agent-loop-lite` generates Markdown + direct-SQLite loops; `houmao-agent-loop-pro` generates schema-rich `tree-loop` or `generic-loop` packages.
- **AG-UI and graphing**: `houmao-ext-graphing` authors validated Plotly (`plotly2d` v3) and Vega-Lite (`v1`) payloads; `houmao-interop-ag-ui` validates, frames, renders, and live-publishes AG-UI events.
