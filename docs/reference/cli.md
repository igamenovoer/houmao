# CLI And Environments

`Houmao` uses a standalone Pixi manifest in this repository.

## Install

```bash
pixi install
```

## Primary Commands

- Supported operator CLI: `houmao-mgr`
- Supported server/API CLI: `houmao-passive-server`
- Removed historical entrypoints: `houmao-cli`, standalone `houmao-server`, and `houmao-cao-server`

Module equivalents:

```bash
houmao-passive-server --help
houmao-mgr --help
```

## Output Style Control

`houmao-mgr` supports three output modes via root-level flags:

- `--print-plain` — Human-readable aligned text (default).
- `--print-json` — Machine-readable JSON (`indent=2`, `sort_keys=True`).
- `--print-fancy` — Rich-formatted output with tables, panels, and colors.

Set `HOUMAO_CLI_PRINT_STYLE=plain|json|fancy` for persistent preference without repeating the flag. Resolution order: explicit flag → env var → `plain`.

High-traffic commands such as `agents global list`, `agents single ... state`, `agents self state`, and scoped gateway status/prompt commands have curated plain and fancy renderers. All other commands use generic fallback renderers that auto-detect payload shape (flat key-value dict, single-list-key table, or nested structure).

Scripts and CI pipelines that parse `houmao-mgr` output as JSON must add `--print-json` or set `HOUMAO_CLI_PRINT_STYLE=json`.

## Common Runtime Flags

Runtime launch is exposed through `houmao-mgr` command families. Historical `houmao-cli start-session`, `cao_rest`, and `houmao_server_rest` workflows are retired and are not packaged as supported commands.

Useful direct native-agent brain-build override:

- `--operator-prompt-mode unattended` to request versioned unattended launch-policy resolution for the built brain
- `--operator-prompt-mode as_is` to keep the provider startup posture unchanged; omitted mode now defaults to `unattended`

For Kimi managed automation, use the Houmao prompt-mode contract: store or pass `launch.prompt_mode: unattended` through the project specialist/profile controls, or use `--operator-prompt-mode unattended` for direct native-agent builds. Houmao then selects the maintained Kimi no-question policy for the chosen backend. Do not use Kimi `--yolo` as a Houmao launch option, and do not require raw `--auto` launch overrides for ordinary managed Kimi TUI automation.

The preferred operator/API surface is `houmao-mgr` for local workflows plus `houmao-passive-server` for API-based coordination.

For pair-managed agents, the supported operator surface is the managed-agent command family on `houmao-mgr` and the matching `/houmao/agents/*` server routes. When an attached gateway is healthy, those same commands automatically gain richer live backing behavior such as gateway-owned admission, queueing, and live state projection without changing the public CLI shape.

Within that pair, `houmao-mgr` is split deliberately:

- `agents` is the managed-agent lifecycle family
- `system-skills` installs, removes, and inspects Houmao-owned skills for resolved Claude, Codex, Kimi Code, or Copilot homes outside managed launch or join, and for the cross-client `universal` target under `~/.agents/skills`
- `project` is the repo-local Houmao overlay family with `agents`, `credentials`, `specialist`, `profile`, and `mailbox` views
- `internals native-agent` is the direct provider-aligned native-agent material family, including internal credential and brain-build plumbing
- `mailbox` is the generic filesystem mailbox-root family for arbitrary roots
- `admin` is the local maintenance family

The repo-local `project` tree is intentionally split by user view:

- `project agents ...` is the low-level compatibility-projection surface for `.houmao/agents/`. Project-local semantic truth lives in `.houmao/catalog.sqlite` plus `.houmao/content/`, while `.houmao/agents/` remains the generated file-tree view used by current builders and runtime. It includes:
    - `internals native-agent roles ...` for prompt-only role management,
    - `internals native-agent recipes ...` (canonical) and `project agents presets ...` (compatibility alias) for named recipe administration under `.houmao/agents/presets/<name>.yaml`,
    - `internals native-agent launch-dossiers ...` for explicit recipe-backed reusable birth-time launch profiles under `.houmao/agents/launch-profiles/<name>.yaml`,
    - `internals native-agent tools <tool> ...` for adapter and setup administration under `.houmao/agents/tools/<tool>/`,
- `project [--project-dir <dir>] credentials ...` is the supported project credential-management family. Use `internals native-agent credentials <tool> ... --native-agent-root <path>` for direct native-agent material.
- `project ...` is the higher-level specialist, project-profile, and instance surface. It includes `project specialist ...`, `project profile ...` (specialist-backed reusable birth-time profiles), and `project agents ...` (the runtime lifecycle surface that accepts `--specialist` or `--profile` on `instance launch`).
- `project mailbox ...` is the project-scoped wrapper over the generic mailbox-root commands.

For the canonical option tables and edge cases on the new `project profile`, `project agents launch`, `internals native-agent recipes`, and `internals native-agent launch-dossiers` surfaces, see [houmao-mgr](cli/houmao-mgr.md). For the conceptual model that ties project profiles and native launch dossiers together, including managed-header whole-header policy, per-section policy, composition, and opt-out rules, see [Launch Profiles](../getting-started/launch-profiles.md).

Managed-agent birth is source-scoped. The maintained public project-backed birth path is `houmao-mgr project [--project-dir <dir>] agents launch --specialist <name>` or `houmao-mgr project [--project-dir <dir>] agents launch --profile <name>`. Root/global/single `houmao-mgr agents launch` paths are retired.

The explicit `houmao-mgr cao ...` namespace and top-level `houmao-mgr launch` are deprecated and removed from the supported command tree.

Useful pair runtime controls:

- `houmao-mgr agents global list` shows active lifecycle records by default. Use `--state stopped`, `--state retired`, or `--state all` when you intentionally want lifecycle-inclusive discovery instead of the normal live-control view.
- `houmao-mgr agents single --agent-name <friendly-name> state|prompt|interrupt|stop|relaunch ...` targets exactly one explicitly selected local managed agent.
- `houmao-mgr agents self join --agent-name <friendly-name> [--workdir <path>]` adopts a supported TUI that is already running in tmux window `0`, pane `0` of the current session, publishes the normal manifest-first runtime envelope, and does not restart the live TUI.
- `houmao-mgr agents self join --headless --agent-name <friendly-name> --provider <provider> --launch-args <arg> ... [--workdir <path>]` adopts a tmux-backed native headless logical session between turns; `--resume-id` is optional, where omitted means start from no known chat, `last` means resume the latest known chat, and any other non-empty value means resume that exact provider session id.
- `houmao-mgr agents self relaunch` refreshes only the active current managed tmux session. Broader stopped/degraded recovery belongs to `houmao-mgr agents single --agent-name <friendly-name> relaunch`.
- `houmao-mgr agents single --agent-name <friendly-name> stop` stops a live tmux-backed managed agent. For local relaunchable sessions, stop preserves a stopped lifecycle registry record with the durable manifest path, session root, last-known tmux session name, and relaunch posture needed for later selected-agent relaunch or cleanup.
Run the maintained server API surface with `houmao-passive-server serve`. Manager commands that accept a pair-authority port default to the passive-server port `9891` when no explicit port is supplied.

Joined-session notes:

- `houmao-mgr agents self join` must be run from inside the target tmux session and, in v1, always adopts tmux window `0`, pane `0` as the canonical managed surface.
- `agents self join` exposes `--workdir` as the public cwd override; when omitted, Houmao derives the adopted workdir from the primary pane current path.
- Successful join publishes the same stable tmux discovery variables used by native launches: `HOUMAO_MANIFEST_PATH`, `HOUMAO_AGENT_ID`, `HOUMAO_NATIVE_AGENT_ROOT`, `HOUMAO_AGENT_MEMORY_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_PAGES_DIR`.
- Joined sessions publish a shared-registry record immediately using a long sentinel lease instead of relying on a background lease-renewal daemon. Later runtime control can refresh that same record opportunistically.
- Joined TUI sessions without recorded `--launch-args` and `--launch-env` remain controllable while live but fail explicitly on later selected-agent `agents single ... relaunch` because restart posture is unavailable by design.
- `--launch-env` follows Docker `--env` style: `NAME=value` stores a literal secret-free binding, while `NAME` means the relaunch resolves that variable from the tmux session environment at relaunch time.

Managed-agent memory commands live under `houmao-mgr agents single ... memory ...` and `houmao-mgr agents self memory ...`. The memo is a free-form `houmao-memo.md` file; page writes under `pages/` do not edit it. Use scoped `memory resolve --path <page>` to return the page-relative path, memo-relative link, absolute path, existence, and kind when an operator or agent wants to author a link manually.

For managed agents, the public gateway control surface lives on `houmao-mgr agents single ... gateway ...` for selected-agent authority and `houmao-mgr agents self gateway ...` for the current managed session. `agents single ... gateway` inherits the group-level `--agent-id` or `--agent-name` selector; `agents self gateway` accepts no explicit selectors. `--pair-port` is available only on selected-agent gateway commands.

For ordinary pair-native prompt submission, prefer `houmao-mgr agents single --agent-name <friendly-name> prompt --prompt "..."` for an explicit selected agent or `houmao-mgr agents self prompt --prompt "..."` inside the current managed session. On headless targets, scoped `prompt`, scoped `gateway prompt`, and scoped `turn submit` also accept request-scoped `--model` plus optional `--reasoning-level`; those overrides apply only to the current turn, use the resolved tool/model preset ladder rather than a portable `1..10` scale, and TUI-backed targets reject them explicitly.

For pair-owned mailbox follow-up, use `houmao-mgr agents single --agent-name <name> mail resolve-live|status|list|peek|read|send|post|reply|mark|move|archive ...` or `houmao-mgr agents self mail ...`. For local artifact or maintenance work that should not hit a server API authority, use `houmao-mgr project init|status`, `houmao-mgr project agents ...`, `houmao-mgr project ...`, `houmao-mgr project mailbox ...`, `houmao-mgr internals native-agent brain build ...` for direct internal native-agent builds, `houmao-mgr admin cleanup registry|runtime ...`, `houmao-mgr agents single ... cleanup ...`, and `houmao-mgr mailbox ...` for arbitrary-root mailbox administration.

For installation or removal of the packaged Houmao-owned skill surface outside managed launch or join, use `houmao-mgr system-skills list|status|install|uninstall ...`. `--home` is optional for single-target install, uninstall, and status commands: omitted `--home` resolves from the tool-native home env var first and otherwise falls back to the project-scoped default home for tool targets, while `--tool universal` resolves to `~/.agents`. `install` can select sets or explicit skills, while `uninstall` removes all current catalog-known Houmao skill paths for the resolved home. That surface is documented in [system-skills](cli/system-skills.md).

Selected-agent cleanup commands under `houmao-mgr agents single ... cleanup session|logs|mailbox` support `--dry-run` and return structured `planned_actions`, `applied_actions`, `blocked_actions`, and `preserved_actions`. Plain and fancy modes print populated cleanup actions line by line, while `--print-json` preserves the machine-readable output. `agents self cleanup` is not a maintained public path.

For API-backed validation, run `houmao-passive-server` on `9891` and target it from `houmao-mgr` commands that accept pair-authority options:

```bash
houmao-mgr agents single --agent-id <agent-id> state --port 9891
houmao-mgr agents single --agent-id <agent-id> turn submit --port 9891 --prompt "Summarize the latest turn."
```

Passive-server gateway attach and detach remain same-host operations. `houmao-mgr agents single --agent-id <agent-id> gateway attach|detach --pair-port 9891` succeeds only when the target can be resolved to a local registry-backed runtime authority on the current host; remote passive-server HTTP attach and detach are intentionally unsupported.

The low-level runtime `mail` command operates on resumed mailbox-enabled sessions and supports `list`, `send`, and `reply` among its TUI-mediated mailbox prompt surfaces.

When `start-session` is used with `--json`, unattended sessions may also return:

- `launch_policy_provenance` with the requested mode, detected CLI version, selected strategy id, and whether resolution came from the registry or the transient override env var
- `launch_policy` with the resolved strategy metadata that was attached to the launch plan

Command reminders:

- `mail send` recipients must use full mailbox addresses such as `HOUMAO-orchestrator@agents.localhost`.
- `mail send` and `mail reply` require body content via `--body-file` or `--body-content`.
- `send-keys` is the low-level control-input surface for resumed legacy compatibility sessions; new standalone `backend="cao_rest"` operator workflows are retired in favor of maintained `houmao-mgr` local workflows and `houmao-passive-server` API workflows.
- Managed-agent routes and `agents ...` commands are the preferred pair seam. The legacy compatibility namespace is no longer part of the supported operator workflow.

For the dedicated mailbox quickstart, contracts, and operational guidance, see [Mailbox Reference](mailbox/index.md).

## Agent Definition Directory

Runtime commands use two agent-definition-directory resolution models:

1. Build/start and manifest-path control: `--agent-def-dir`, then `HOUMAO_NATIVE_AGENT_ROOT`, then `HOUMAO_PROJECT_OVERLAY_DIR`, then ambient project-overlay discovery under `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`, then `<pwd>/.houmao/agents`.
2. Name-based tmux-backed `send-prompt`, `send-keys`, `mail`, and `stop-session`: explicit `--agent-def-dir` override first, otherwise the addressed session's published `HOUMAO_NATIVE_AGENT_ROOT`.

`HOUMAO_PROJECT_OVERLAY_DIR` must be an absolute path and selects the overlay directory directly. `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` controls only ambient discovery when no explicit overlay root is set: `ancestor` is the default nearest-ancestor lookup bounded by the Git repository, while `cwd_only` inspects only `<cwd>/.houmao/houmao-config.toml`. When env selection or discovery finds `houmao-config.toml`, the selected overlay directory becomes the project-overlay discovery anchor, and relative paths in that config resolve from the overlay directory itself. For current pair-native build and launch flows, Houmao materializes `agents/` under the selected catalog-backed overlay as the compatibility projection that file-tree consumers read.

## Pixi Tasks

```bash
pixi run format
pixi run lint
pixi run typecheck
pixi run test-runtime
pixi run build-dist
pixi run check-dist
```
