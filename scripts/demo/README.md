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

Headless lanes run a full `launch -> prompt -> state -> stop` cycle. TUI lanes run `launch -> state`, leave the agent alive, and surface the tmux attach handoff for non-interactive callers.

Start here:

- [Tutorial: minimal-agent-launch/tut-agent-launch-minimal.md](minimal-agent-launch/tut-agent-launch-minimal.md)
- Runner: [minimal-agent-launch/scripts/run_demo.sh](minimal-agent-launch/scripts/run_demo.sh)

## Archived Reference

### `legacy/`

Historical demo packs preserved for reference while the old demo surface is retired.

They are useful for redesign context and implementation history, but they are not part of the maintained operator surface and they do not define current product requirements.
