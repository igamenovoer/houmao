# Concepts

Use this reference when `houmao-admin-welcome` needs to ground vocabulary for a first-time user or when a path cites an unfamiliar term. Keep definitions short; deeper detail lives in the parent-scoped shared routine named at the end of each entry.

This reference is self-contained. It does not depend on any file outside the packaged `houmao-admin-welcome/` asset directory. An owning routine name is a stable child id, not a bare public skill invocation. For normal human-operator work, route it through `$houmao-admin-entrypoint <route-name> ...`; advanced users may invoke `$houmao-shared-routines <route-name> ...` directly.

## Project and Layout

- **Project overlay** — the `.houmao/` directory that holds a Houmao project's specialists, credentials, mailbox, memory, catalog, and configuration. A workspace becomes a Houmao project once that overlay is created. Owning routine: `houmao-project-mgr`.
- **Recipe** — a reusable build-phase bundle of role prompt, tool adapter, skills, and setup or authentication assets. Recipes drive the build phase that produces a managed agent's runtime home. Owning routine: `houmao-agent-definition`.
- **Tool adapter** — the per-tool contract that tells Houmao how to build and launch one CLI agent family (for example `claude`, `codex`, or `kimi`). Owning routine: `houmao-agent-definition`.

## Agents, Specialists, Profiles, Launches

- **Agent Definition Revision** — a portable immutable package derived from user-owned intent. It can declare typed deploy inputs, prompts, memo content, complete skills, runtime variables, named mindsets, and optional private-workspace behavior. Owning routine: `houmao-agent-definition` subcommand `definition-authoring`.
- **Agent Deployment** — the durable project relationship created when one exact Agent Definition Revision and deploy-time values resolve into specialist, profile, skills, and launch-ready instance contracts. Deployment returns a launch command and does not run it. Owning routine: `houmao-agent-definition` subcommand `definition-deployment`.
- **Specialist** — a reusable agent template that pairs a role prompt, tool adapter, and credentials under one name. You can launch a specialist more than once. Owning routine: `houmao-agent-definition`.
- **Project profile** — an optional reusable launch-default wrapper layered on top of a specialist. It captures birth-time defaults such as a fixed instance name, working directory, authentication lane, or mailbox posture. Owning routine: `houmao-agent-definition`.
- **Launch dossier** — the low-level recipe-backed launch-profile object that can be attached to a build request to carry reusable birth-time defaults such as managed-agent identity, workdir, auth override, prompt mode, durable env records, mailbox config, gateway posture, and managed-header policy. Owning routine: `houmao-agent-definition` subcommand `launch-dossiers`.
- **Managed agent** — the running live instance of an agent that Houmao supervises inside a real tmux session. A managed agent has its own disk state, memory, gateway sidecar, and mailbox binding. Owning routine: `houmao-agent-instance`.
- **Relaunch** — restart a relaunchable managed session without treating it as a fresh launch. Relaunch preserves the original managed-agent identity and supporting artifacts. Owning routine: `houmao-agent-instance`.
- **Cleanup** — remove artifacts for a stopped managed-agent session. Cleanup takes a cleanup kind such as `session` or `logs` and is never safe for a live session. Owning routine: `houmao-agent-instance`.
- **Runtime variable** — a non-secret typed value stored per managed-agent instance with revision history. Launch uses one snapshot, while declared live-consuming skills read the current value at use time. Owning routine: `houmao-agent-instance` subcommand `runtime-variables`.
- **Named mindset** — a revisioned question set referenced by name. A bound skill takes one atomic snapshot before work; a private-workspace copy is only a projection. Owning routine: `houmao-agent-instance` subcommand `mindsets`.

## Gateway, Posture, Watch

- **Gateway** — the per-agent HTTP control sidecar that Houmao attaches next to a managed agent. The gateway exposes the agent's live capabilities (prompt, state, mail, notifier, reminders). Owning routine: `houmao-agent-gateway`.
- **Gateway sidecar** — the tmux window or background process in which the gateway runs alongside the managed-agent window. A foreground gateway sidecar is visible in a non-zero auxiliary tmux window. Owning routine: `houmao-agent-gateway`.
- **Foreground vs background posture** — whether the gateway sidecar runs in a visible tmux window (foreground) or detached as a background process. First-run tour launches prefer foreground posture unless the user explicitly asks for background or detached execution. Owning routine: `houmao-agent-gateway`.
- **Execution mode** — the gateway status field that reports whether the current gateway is running in foreground or background. Use this field to explain current posture; do not infer posture from tmux window names. Owning routine: `houmao-agent-gateway`.
- **Notifier round** — one bounded turn of work triggered by gateway mail-notifier reporting open mailbox work through a prompt-provided gateway base URL. The agent processes selected open mail, replies after successful work when needed, archives only successfully processed mail, and then stops until the next notification. Owning routine: `houmao-process-emails-via-gateway`.

## Mailbox

- **Mailbox root** — the shared filesystem or JMAP root used by a Houmao project so that managed agents can send and receive mail. Initializing the mailbox root is separate from creating an individual mailbox account. Owning routine: `houmao-mailbox-mgr`.
- **Mailbox account** — one per-agent or shared mailbox identity (address plus principal id) registered under the mailbox root. An easy-instance launch can own per-agent mailbox accounts for addresses like `<agent-name>@houmao.localhost`, so it is not always necessary to preregister them manually. Owning routine: `houmao-mailbox-mgr`.
- **Principal id** — the Stalwart principal identifier bound to a mailbox account. Houmao reserves local parts beginning with `HOUMAO-` under `houmao.localhost` for system principals. Owning routine: `houmao-mailbox-mgr`.
- **Prompt injection through mail** — an intentional workflow where mailbox content is used as the carrier for an agent instruction, either through ordinary shared-mailbox operations or a notifier-driven round. It is an intermediate live-operation pattern, not a hidden side effect of every mailbox message. Owning routines: `houmao-agent-email-comms` and `houmao-process-emails-via-gateway`.

## Roles in a Multi-Agent Run

- **User agent** — the agent (human or CLI) that interacts with the user and composes Houmao plans. The user agent stays outside the execution loop; it plans, starts, checks, and stops rather than driving local-close edges directly. Owning routine: the top-level `houmao-admin-welcome` tour and the loop skills.
- **Master** — an optional designated managed agent that owns supervision, downstream dispatch, completion evaluation, and stop handling when a generated loop design chooses central ownership. Owning routine: `houmao-agent-loop-lite` or `houmao-agent-loop-pro`.
- **Loop plan** — generated execplan artifacts that define objective, participants, communication, generated skills, state, agent bindings, and run behavior. Lite plans use Markdown contracts with direct SQLite state; pro plans add schema-rich topology, harness behavior, workspace contracts, and run-control behavior. Owning routine: `houmao-agent-loop-lite` or `houmao-agent-loop-pro`.
- **Lite loop** — a lightweight generated loop package that uses Markdown contracts, typed Markdown templates, generated skills, and direct SQLite state without a generated harness or docs layer. Owning routine: `houmao-agent-loop-lite`.
- **Pro loop** — a schema-rich generated loop package that can include topology contracts, mail schemas, harness behavior, workspace contracts, generated skills, validation, participant launch, and run-control actions. Owning routine: `houmao-agent-loop-pro`.
- **Tree-loop** — a topology mode inside `houmao-agent-loop-pro` for local-close tree-shaped downstream work where results return to immediate upstream owners unless the generated execplan explicitly records relay choices. Owning routine: `houmao-agent-loop-pro`.
- **Generic-loop** — a topology mode inside `houmao-agent-loop-pro` for graphs that may include cycles, relay lanes, or task-specific predecessor-context forwarding choices. Owning routine: `houmao-agent-loop-pro`.

## Workspaces

- **Isolated workspace** — a prepared multi-agent workspace layout that gives agents controlled per-agent worktrees, local shared repos, knowledge directories, safe local-state symlinks, and launch-profile cwd rules before agents are launched. Owning routine: `houmao-utils-workspace-mgr`.
- **Workspace contract** — the human-readable record of a prepared workspace's layout, read/write ownership, Git branches, submodule decisions, launch-profile cwd changes, and optional memo-seed workspace rules. Owning routine: `houmao-utils-workspace-mgr`.
- **Private Agent Workspace** — one optional definition-owned auxiliary workspace for an individual agent, with TOML semantic path mappings, a SQLite record index, and local-untracked Git posture by default. It is separate from multi-agent workspace topology. Owning routine: `houmao-agent-instance` subcommand `private-workspace`.

## Memory and Pages

- **Managed-agent memo** — each managed agent's free-form `houmao-memo.md` file held inside the project overlay. Agents and users can read and write it through the memory skill. Owning routine: `houmao-memory-mgr`.
- **Pages** — structured named memory entries under the managed-agent memory root, usable for longer-lived notes that do not belong in the free-form memo. Owning routine: `houmao-memory-mgr`.

## Cross-References

Every definition above names an owning shared routine or top-level loop sibling. When the tour needs to explain how to act on a concept, hand the turn to `$houmao-admin-entrypoint` with that route name rather than presenting a parent-scoped child as a standalone skill.
