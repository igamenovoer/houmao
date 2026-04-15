# Concepts

Use this reference when `houmao-touring` needs to ground vocabulary for a first-time user or when a branch cites a term the user is unfamiliar with. Keep definitions short; deeper detail lives on the owning skill named at the end of each entry.

This reference is self-contained. It does not depend on any file outside the packaged `houmao-touring/` asset directory.

## Project And Layout

- **Project overlay** — the `.houmao/` directory that holds a Houmao project's specialists, credentials, mailbox, memory, catalog, and configuration. A workspace becomes a Houmao project once that overlay is created. Owning skill: `houmao-project-mgr`.
- **Recipe** — a reusable build-phase bundle of role prompt, tool adapter, skills, and setup or authentication assets. Recipes drive the build phase that produces a managed agent's runtime home. Owning skill: `houmao-agent-definition`.
- **Tool adapter** — the per-tool contract that tells Houmao how to build and launch one CLI agent family (for example `claude`, `codex`, `gemini`). Owning skill: `houmao-agent-definition`.

## Agents, Specialists, Profiles, Launches

- **Specialist** — a reusable agent template that pairs a role prompt, tool adapter, and credentials under one name. A specialist can be launched more than once. Owning skill: `houmao-specialist-mgr`.
- **Easy profile** — an optional reusable launch-default wrapper layered on top of a specialist. It captures birth-time defaults such as a fixed instance name, working directory, authentication lane, or mailbox posture. Owning skill: `houmao-specialist-mgr`.
- **Launch profile** — the explicit launch-profile object that can be attached to a build request to carry reusable birth-time defaults such as managed-agent identity, workdir, auth override, prompt mode, durable env records, mailbox config, gateway posture, and managed-header policy. Owning skill: `houmao-project-mgr`.
- **Managed agent** — the running live instance of an agent that Houmao supervises inside a real tmux session. A managed agent has its own disk state, memory, gateway sidecar, and mailbox binding. Owning skill: `houmao-agent-instance`.
- **Relaunch** — restart a relaunchable managed session without treating it as a fresh launch. Relaunch preserves the original managed-agent identity and supporting artifacts. Owning skill: `houmao-agent-instance`.
- **Cleanup** — remove artifacts for a stopped managed-agent session. Cleanup takes a cleanup kind such as `session` or `logs` and is never safe for a live session. Owning skill: `houmao-agent-instance`.

## Gateway, Posture, Watch

- **Gateway** — the per-agent HTTP control sidecar that Houmao attaches next to a managed agent. The gateway exposes the agent's live capabilities (prompt, state, mail, notifier, reminders). Owning skill: `houmao-agent-gateway`.
- **Gateway sidecar** — the tmux window or background process in which the gateway runs alongside the managed-agent window. A foreground gateway sidecar is visible in a non-zero auxiliary tmux window. Owning skill: `houmao-agent-gateway`.
- **Foreground vs background posture** — whether the gateway sidecar runs in a visible tmux window (foreground) or detached as a background process. First-run tour launches prefer foreground posture unless the user explicitly asks for background or detached execution. Owning skill: `houmao-agent-gateway`.
- **Execution mode** — the gateway status field that reports whether the current gateway is running in foreground or background. Use this field to explain current posture; do not infer posture from tmux window names. Owning skill: `houmao-agent-gateway`.

## Mailbox

- **Mailbox root** — the shared filesystem or JMAP root used by a Houmao project so that managed agents can send and receive mail. Initializing the mailbox root is separate from creating an individual mailbox account. Owning skill: `houmao-mailbox-mgr`.
- **Mailbox account** — one per-agent or shared mailbox identity (address plus principal id) registered under the mailbox root. An easy-instance launch can own per-agent mailbox accounts for addresses like `<agent-name>@houmao.localhost`, so it is not always necessary to preregister them manually. Owning skill: `houmao-mailbox-mgr`.
- **Principal id** — the Stalwart principal identifier bound to a mailbox account. Local parts beginning with `HOUMAO-` under `houmao.localhost` are reserved for Houmao-owned system principals. Owning skill: `houmao-mailbox-mgr`.

## Roles In A Multi-Agent Run

- **User agent** — the agent (human or CLI) that interacts with the user and composes Houmao plans. The user agent stays outside the execution loop; it plans, starts, checks, and stops rather than driving pairwise edges directly. Owning skill: the top-level `houmao-touring` tour and the loop skills.
- **Master** — the designated managed agent that owns supervision, downstream dispatch, completion evaluation, and stop handling after accepting a loop run. Owning skills: `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-generic`.
- **Loop plan** — a single-file or bundle plan that names a master, participants, and the intended pairwise or relay topology. The plan is the author-time artifact that the loop skills consume at `start`. Owning skills: `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-generic`.

## Memory And Pages

- **Managed-agent memo** — each managed agent's free-form `houmao-memo.md` file held inside the project overlay. Agents and users can read and write it through the memory skill. Owning skill: `houmao-memory-mgr`.
- **Pages** — structured named memory entries under the managed-agent memory root, usable for longer-lived notes that do not belong in the free-form memo. Owning skill: `houmao-memory-mgr`.

## Cross-references

Every definition above names an owning skill. When the tour needs to explain how to act on a concept, route the turn through that skill rather than restating its command shape here.
