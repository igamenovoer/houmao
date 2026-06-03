# Subsystem Exploration

Use this branch when the user explicitly asks `houmao-touring` to explore Houmao by subsystem, component area, ownership boundary, or working logic. This branch serves component-minded users. It is not the default outcome path, not a first-agent quickstart, and not a full packaged skill catalog.

## Opening Map

Present this compact component map before asking which subsystem the user wants to inspect.

| Pick | Subsystems | Best For |
| --- | --- | --- |
| 1 | Project overlay | Understanding where Houmao state lives. |
| 2 | Agent definition | Understanding how agents become launchable. |
| 3 | Managed runtime + Gateway | Understanding live process control. |
| 4 | Messaging + Mailbox | Understanding communication paths. |
| 5 | Memory + Inspection | Understanding durable context and evidence. |
| 6 | Workspace + Loop orchestration | Understanding multi-agent structure. |

If the user names one subsystem directly, skip the map after a short acknowledgement and explain that subsystem.

## Explanation Shape

Each subsystem explanation should cover these parts without forcing one rigid template onto every response.

| Part | Purpose |
| --- | --- |
| Boundary | What this subsystem owns. |
| Required input | What the user or environment must provide. |
| Generated state | What Houmao creates or changes. |
| Operations | Main things the user can do. |
| Routes | Owning skill for concrete work. |
| Next choices | Nearby subsystem or fast-path choices. |

Keep ordinary output compact. Use `more detail` before expanding into command examples, raw status output, passive server context, deeper TUI tracking behavior, advanced internals, or deeper architecture explanation.

## Subsystem Map

### Project Overlay

| Part | Content |
| --- | --- |
| Boundary | Project-local `.houmao/` state, catalogs, credentials references, mailbox root, memory roots, and runtime metadata. |
| Required input | A workspace path and the user's choice to initialize or inspect project state. |
| Generated state | Project overlay files and records used by later agent definition, mailbox, memory, and runtime operations. |
| Routes | Concrete project setup and explanation belong to `houmao-project-mgr`. |

Nearby choices: Agent definition when the user wants launchable agents; Mailbox when they want communication state; Single Agent Full Run when they want to build now.

### Agent Definition

| Part | Content |
| --- | --- |
| Boundary | Recipes, roles, tool adapters, credentials, specialists, project profiles, launch dossiers, and easy-instance launch defaults. |
| Required input | Intended role, tool adapter, credential posture, optional profile defaults, and launch intent. |
| Generated state | Specialist/profile records and launch inputs that can create managed agents. |
| Routes | Specialist, profile, launch dossier, fast-forward, and launch work belong to `houmao-agent-definition`; credential content work belongs to `houmao-credential-mgr`. |

Nearby choices: Managed runtime after launch; Memory for memo-seed context; Single Agent Full Run for an end-to-end path.

### Managed Runtime

| Part | Content |
| --- | --- |
| Boundary | Live tmux-backed managed sessions, runtime identity, lifecycle state, relaunchability, and cleanup eligibility. |
| Required input | Target managed-agent name or a request to list current agents. |
| Generated state | Runtime session records, logs, gateway bindings, mailbox bindings, and lifecycle artifacts. |
| Routes | Stop, relaunch, join/adopt, list, and cleanup belong to `houmao-agent-instance`; read-only runtime evidence belongs to `houmao-agent-inspect`. |

Nearby choices: Gateway for live sidecar control; Messaging for prompt entry; Lifecycle follow-up when the user wants stop/relaunch/cleanup.

### Gateway

| Part | Content |
| --- | --- |
| Boundary | Per-agent HTTP sidecar for live prompt/state control, TUI watch, mail-notifier, reminders, and gateway posture. |
| Required input | Target managed agent and, when needed, current gateway availability or base URL. |
| Generated state | Gateway process or sidecar posture, notifier state, reminder state, and live capability endpoints. |
| Routes | Gateway lifecycle, watch, mail-notifier, and reminders belong to `houmao-agent-gateway`. |

Nearby choices: Messaging for direct prompts; Mailbox for mail-triggered work; Inspection for state evidence.

### Messaging

| Part | Content |
| --- | --- |
| Boundary | Operator intent entering a running agent through direct prompt, interrupt, raw input, queue, or mailbox-routed handoff. |
| Required input | Target agent and intended delivery mode. |
| Generated state | Prompt/input delivery records or mailbox-routed work depending on selected transport. |
| Routes | Direct prompt, interrupt, raw input, and mailbox-routing entry belong to `houmao-agent-messaging`; ordinary mailbox send/read/reply/post/archive belongs to `houmao-agent-email-comms`. |

Nearby choices: Mailbox when work should be durable mail; Gateway when the agent should be controlled through live gateway features; Operator-Controlled Agent Team for manual multi-agent work.

### Mailbox

| Part | Content |
| --- | --- |
| Boundary | Mailbox roots, accounts, addresses, principal ids, operator-origin mail, inter-agent mail, and notifier-triggered open-mail work. |
| Required input | Mailbox root/account intent, target sender/recipient identities, and whether mail is ordinary communication or prompt carrier. |
| Generated state | Mailbox root/account records, messages, archives, replies, and notifier-visible open mail. |
| Routes | Mailbox administration belongs to `houmao-mailbox-mgr`; ordinary mail operations belong to `houmao-agent-email-comms`; one gateway-notified processing round belongs to `houmao-process-emails-via-gateway`. |

Nearby choices: Gateway for mail-notifier; Messaging for immediate prompt; Memory when durable context should not be mail.

### Memory

| Part | Content |
| --- | --- |
| Boundary | Managed-agent memo and pages for durable context that should remain available across later work. |
| Required input | Target agent/profile and the memo or page content to read, write, or seed. |
| Generated state | Memo text, named pages, and optional launch-profile memo-seed records. |
| Routes | Memo, pages, and launch-profile memo-seed work belong to `houmao-memory-mgr`. |

Nearby choices: Inspection to verify live posture; Messaging to use context in a prompt; Agent definition when seeding future launch profiles.

### Inspection

| Part | Content |
| --- | --- |
| Boundary | Read-only evidence about state, screen posture, logs, turn evidence, mailbox posture, gateway posture, and runtime artifacts. |
| Required input | Target managed agent, target evidence type, or permission to list candidates. |
| Generated state | No intended mutation; the result is evidence for the next decision. |
| Routes | Managed-agent inspection belongs to `houmao-agent-inspect`; gateway-specific status belongs to `houmao-agent-gateway`. |

Nearby choices: Messaging after deciding what to say; Gateway after seeing sidecar state; Lifecycle follow-up after seeing stopped or stale sessions.

### Workspace

| Part | Content |
| --- | --- |
| Boundary | Isolated multi-agent working directories, per-agent worktrees, local shared repos, safe local-state symlinks, and workspace contracts. |
| Required input | Agent roster, intended workspace layout, repository safety constraints, and whether launches should inherit workspace cwd values. |
| Generated state | Workspace plan, prepared directories or worktrees, validation reports, launch-profile cwd updates, and optional memo-seed workspace rules. |
| Routes | Workspace planning, creation, validation, and summaries belong to `houmao-utils-workspace-mgr`. |

Nearby choices: Loop orchestration when workspaces support generated loops; Agent definition when profiles need workspace cwd; Operator-Controlled Agent Team when manual agents need separate work areas.

### Loop Orchestration

| Part | Content |
| --- | --- |
| Boundary | Generated loop intent, participant roles, topology, contracts, validation, launch, operation, and run-control behavior. |
| Required input | Loop objective, participants, handoff model, mailbox/runtime contracts, and topology choice. |
| Generated state | Execplan artifacts, generated skills, contracts, optional workspaces, participant bindings, and loop operation state. |
| Routes | Schema-rich topology-heavy loops belong to `houmao-agent-loop-pro`; lightweight Markdown/direct-SQL loops belong to `houmao-agent-loop-lite`; workspace preparation belongs to `houmao-utils-workspace-mgr`. |

Nearby choices: Pro Agent Loop for generated construction; Workspace when isolated directories are needed; Mailbox when communication contracts need grounding.

## Detail Boundary

Do not show passive server internals, deeper TUI tracking behavior, raw command output, command examples, or deeper architecture by default. If the user asks for `more detail`, expand only the selected subsystem and keep concrete operation ownership on the route named for that subsystem.
