# Demo Surface

This directory contains the small supported runnable demos that complement the main documentation.

## Supported Demo

### `minimal-agent-launch/`

Tutorial-shaped example showing the smallest canonical `agents/` tree needed to launch one managed agent across the full supported Claude/Codex × headless/TUI matrix.

Supported lanes:

- `--provider claude_code` for the default Claude TUI lane
- `--provider claude_code --headless` for the Claude headless lane
- `--provider codex` for the default Codex TUI lane
- `--provider codex --headless` for the Codex headless lane

The shared runner defaults to TUI and only needs `--headless` for the headless lane:

```bash
scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider <claude_code|codex> [--headless]
```

Headless lanes run a full `launch -> prompt -> state -> stop` cycle. TUI lanes run `launch -> state`, leave the agent alive, and surface the tmux attach handoff for non-interactive callers. The runner materializes one generated overlay root under `outputs/<provider>[-headless]/workdir/.houmao/`, so agent definitions plus runtime and jobs state stay together without extra root overrides.

Start here:

- [Tutorial: minimal-agent-launch/tut-agent-launch-minimal.md](minimal-agent-launch/tut-agent-launch-minimal.md)
- Runner: [minimal-agent-launch/scripts/run_demo.sh](minimal-agent-launch/scripts/run_demo.sh)

### `shared-tui-tracking-demo-pack/`

Standalone shared tracked-TUI demo pack for live tmux observation, optional recorder-backed watch runs, scenario-driven recorded capture, strict replay validation, and cadence sweeps. The supported pack owns a tracked secret-free `inputs/agents/` tree and materializes a run-local `workdir/.houmao/agents` tree with a demo-local `auth: default` alias for the selected tool.

Start here:

- [Guide: shared-tui-tracking-demo-pack/README.md](shared-tui-tracking-demo-pack/README.md)
- Runner: [shared-tui-tracking-demo-pack/run_demo.sh](shared-tui-tracking-demo-pack/run_demo.sh)

### `single-agent-mail-wakeup/`

Supported project-local gateway wake-up demo for one `houmao-mgr project easy` TUI specialist. The pack keeps one canonical `outputs/` root, copies a tiny dummy project under `outputs/project/`, redirects Houmao overlay state into the sibling `outputs/overlay/` root through `HOUMAO_PROJECT_OVERLAY_DIR`, keeps runtime, jobs, and mailbox state under that overlay, imports the local Claude or Codex fixture auth bundle, launches one project-easy TUI instance, attaches a gateway, enables mail-notifier polling, injects one filesystem-backed operator message, and verifies artifact creation plus actor-scoped unread completion.

Supported lanes:

- `claude`
- `codex`

Start here:

- [Guide: single-agent-mail-wakeup/README.md](single-agent-mail-wakeup/README.md)
- Runner: [single-agent-mail-wakeup/run_demo.sh](single-agent-mail-wakeup/run_demo.sh)

### `single-agent-gateway-wakeup-headless/`

Supported project-local gateway wake-up demo for one `houmao-mgr project easy` headless specialist. The pack keeps one canonical `outputs/` root, copies a tiny dummy project under `outputs/project/`, redirects Houmao overlay state into `outputs/overlay/`, imports the local Claude, Codex, or Gemini fixture auth bundle, launches one project-easy instance through `project easy instance launch --headless`, attaches a live gateway in a separate watchable tmux window, enables mail-notifier polling, injects one filesystem-backed operator message, and verifies headless last-turn or durable turn-artifact evidence alongside artifact creation and actor-scoped unread completion.

Supported lanes:

- `claude`
- `codex`
- `gemini`

The canonical Gemini lane uses `tests/fixtures/agents/tools/gemini/auth/personal-a-default` so the supported pack validates the OAuth-backed unattended path.

Start here:

- [Guide: single-agent-gateway-wakeup-headless/README.md](single-agent-gateway-wakeup-headless/README.md)
- Runner: [single-agent-gateway-wakeup-headless/run_demo.sh](single-agent-gateway-wakeup-headless/run_demo.sh)

## Archived Reference

### `legacy/`

Historical demo packs preserved for reference while the old demo surface is retired.

They are useful for redesign context and implementation history, but they are not part of the maintained operator surface and they do not define current product requirements.
