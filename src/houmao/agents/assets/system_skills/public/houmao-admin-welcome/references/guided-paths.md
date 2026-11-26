# Guided Paths

Load only the selected path. Keep welcome strictly read-only; when the operator wants execution, emit the `$houmao-admin-entrypoint` handoff from [admin-handoff.md](admin-handoff.md) with all confirmed facts. Mention `houmao-mgr manual` when CLI reference reading helps.

## Single Agent Full Run

Reach and operate one complete managed agent.

1. Explain how `.houmao/` stores definitions, `project skills`, credentials, mailbox state, and memory without replacing the working tree.
2. Check installed CLIs read-only without choosing for the user: `command -v claude`, `command -v codex`, `command -v dsh`, and `command -v kimi || command -v kimi-code`. Summarize qualified run modes (`claude`: `headless|tui`; `codex`: `headless|service|tui`; `kimi`: `headless|service|tui|web`; `dsh`: `headless|service|web`).
3. Explain specialist, optional project profile, credential lane, working directory (or `--executor`), `system_skills` default `agent` pack, and gateway/mailbox options.
4. Explain what launch creates (identity, mode-appropriate session, optional gateway dashboard/sidecar, offline or Stalwart online mail slot, memo, and usage tracking) and follow-ups (`agent-inspect`, `request`/`prompt`, `open-browser`, `memory-mgr`, `agent-email-comms`, `agent-access`, `agent-files`, `stop`/`relaunch`).

Recover before handoff: project path, tool (`claude|codex|dsh|kimi`), credential name (never secret values), role/specialist intent, run mode, workdir, and gateway/mailbox posture.

```text
$houmao-admin-entrypoint agent-definition create-agent-fast-forward
Selected guided path: Single Agent Full Run
Explicit project target: <path>
Tool, mode, and credential: <tool>, <mode>, <credential-name>
Definition and launch choices: <facts>
Unresolved required inputs: <items-or-none>
```

If the target agent already exists, hand off to `agent-inspect`, `agent-messaging`, `memory-mgr`, `agent-email-comms`, `agent-gateway`, `agent-access`, `agent-files`, or `agent-instance`.

## Operator-Controlled Agent Team

Coordinate multiple local or external agents while keeping the human operator outside their loop.

1. Inventory intended roles, tools/modes, credentials, `--executor` contexts, or remote `agents external` imports.
2. Compare shared workdirs vs isolated Git worktrees via `utils-workspace-mgr` (including DSH Web `--workdir` and `--executor` paths).
3. Compare communication channels: attributed `request` (`agent-requester`), direct `prompt` (`agent-operator`), operator/peer mail (`offline` or Stalwart `online`), `houmao-cccc` group chat/queues, and `operator-messaging` clarify-then-dispatch.
4. Explain per-agent access policy (`default-group`, role templates), usage/state inspection, and independent `stop`/`relaunch`/`cleanup`.

Require explicit project path and target agent IDs/names or proposed definitions before handoff (`$houmao-admin-entrypoint utils-workspace-mgr plan` for layout, or `$houmao-admin-entrypoint operator-messaging clarify` for live targets).

## Pro Agent Loop

Design and run a generated multi-agent loop (`$houmao-admin-entrypoint agent-loop-pro init`, or `agent-loop-lite` when lightweight Markdown + direct SQLite is preferred).

1. Clarify loop objective, completion criteria, participants, artifacts, and failure policy.
2. Compare `tree-loop` (local-close parent-child returns) vs `generic-loop` (cycles and relay lanes), or `adv-usage-pattern` when full loop generation is unnecessary.
3. Outline `intention` -> `execplan` authoring, `prepare-agents` (`headless|service|tui|web`, `dsh`, `project skills`, `system_skills`), `prepare-workspace`, `validate-loop`, `launch-agents` (`--tmux-server`, `--executor`), and `start|status|pause|resume|recover|stop`.

Require an explicit `<loop-dir>` and project target before handoff.

## Subsystem Exploration

Offer a compact read-only subsystem menu (`<= 4` columns) grounded in [concepts.md](concepts.md):

| Area | Key Surfaces | Primary Entrypoint Routes |
| --- | --- | --- |
| Project & definitions | `.houmao/`, `project skills|migrate`, `system-skills`, `claude|codex|dsh|kimi` credentials, specialists, deployments | `project-mgr`, `credential-mgr`, `agent-definition` |
| Runtime & inspection | `headless|service|tui|web`, `--executor`, `agents external`, `open-browser`, usage (`/v1/usage`), memory | `agent-instance`, `agent-inspect`, `memory-mgr` |
| Access, files & gateway | Dashboard `admin_mode`, `default-group`, `self-key`, `skills`/`mcp` mounts (`--when-idle`), reminders, notifier | `agent-gateway`, `agent-access`, `agent-files` |
| Comms, teams & UI | `request` vs `prompt`, offline & Stalwart `mailbox online`, `houmao-cccc`, worktrees, `lite`/`pro` loops, AG-UI/graphics | `agent-messaging`, `mailbox-mgr`, `agent-email-comms`, `adv-usage-pattern`, `utils-workspace-mgr`, `interop-ag-ui`, `ext-graphing` |

## Existing Project Reorientation

Continue from observed `.houmao/` or runtime state without restarting from `init`:

1. Summarize `project status`, registered `project skills`, specialists, and profiles without reading secret values.
2. Summarize `agents global list` and `agents external list` posture with explicit IDs.
3. Note material gateway (`admin_mode`), mailbox (`offline`/`online`), usage, workspace, or loop artifacts only where present.
4. Recommend one concrete `$houmao-admin-entrypoint` continuation (for example `agent-inspect discover for <agent-id>`) and offer `more detail` or path switching.
