---
tutorial_name: minimal-agent-launch
created_at: 2026-03-28T10:45:10Z
base_commit: 6235cc4cb62c79b395723393b1c213de4cc516d6
topic: Houmao - Minimal Agent Launch Demo
runtime:
  os: Linux
  python: 3.13.12
  device: cpu
  notes: Headless local demo verified against fixture auth bundles under tests/fixtures/agents/tools.
---

# How to launch one minimal Houmao agent with Claude or Codex

## Question

How do I define the smallest canonical `agents/` tree that can launch one managed agent through Houmao, while keeping auth local-only and still supporting both Claude and Codex?

## Prerequisites

This tutorial assumes prerequisites are already met; it does not walk through full setup.

- **Environment:** run commands from the repository root with `pixi run ...`
- **Tools:** `tmux` plus the provider CLI you want to use: `claude` or `codex`
- **Configuration:** local fixture auth bundles already restored under `tests/fixtures/agents/tools/claude/auth/kimi-coding` and `tests/fixtures/agents/tools/codex/auth/yunwu-openai`
- **Data:** the tracked prompt file is [inputs/prompt.txt](inputs/prompt.txt)

## Implementation Idea

The tracked demo keeps only the secret-free part of the canonical layout:

- one shared role prompt
- one Claude preset and one Codex preset
- one secret-free setup bundle per tool
- an empty `skills/` root so the builder sees a valid skills repository even though the presets use `skills: []`

At run time, the script copies those tracked inputs into a generated workdir, creates a demo-local `default` auth symlink for the selected provider, points Houmao at that generated `agents/` tree, and runs a headless `launch -> prompt -> state -> stop` cycle.

## Critical Example Code

### Bash

```bash
provider="codex"  # or claude_code
tool="codex"
run_root="scripts/demo/minimal-agent-launch/outputs/${provider}"
generated_agent_def_dir="${run_root}/workdir/.agentsys/agents"

rm -rf "${run_root}/workdir" "${run_root}/runtime"
mkdir -p "${generated_agent_def_dir}"
cp -R scripts/demo/minimal-agent-launch/inputs/agents/. "${generated_agent_def_dir}/"

# Keep auth local-only. The tracked preset uses auth: default, and the script
# binds that alias to one provider-specific fixture auth bundle at run time.
mkdir -p \
  "${generated_agent_def_dir}/tools/claude/auth" \
  "${generated_agent_def_dir}/tools/codex/auth"
ln -s \
  "$PWD/tests/fixtures/agents/tools/codex/auth/yunwu-openai" \
  "${generated_agent_def_dir}/tools/${tool}/auth/default"

AGENTSYS_AGENT_DEF_DIR="$PWD/${generated_agent_def_dir}" \
AGENTSYS_GLOBAL_RUNTIME_DIR="$PWD/${run_root}/runtime" \
pixi run houmao-mgr agents launch \
  --agents minimal-launch \
  --provider "${provider}" \
  --agent-name "minimal-launch-demo-${tool}" \
  --headless \
  --yolo
```

For the full runnable flow, use the tracked script instead of retyping the steps:

```bash
scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider claude_code
scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider codex
```

## Input and Output

### Input

The tracked demo inputs are:

- `inputs/agents/roles/minimal-launch/system-prompt.md`: one shared role prompt
- `inputs/agents/roles/minimal-launch/presets/claude/default.yaml`: minimal Claude preset
- `inputs/agents/roles/minimal-launch/presets/codex/default.yaml`: minimal Codex preset
- `inputs/agents/tools/claude/...`: secret-free Claude adapter and setup
- `inputs/agents/tools/codex/...`: secret-free Codex adapter and setup
- `inputs/prompt.txt`: the prompt submitted after launch

The tracked minimal agent-definition tree is:

```text
scripts/demo/minimal-agent-launch/inputs/agents/
├── skills/
├── roles/
│   └── minimal-launch/
│       ├── system-prompt.md
│       └── presets/
│           ├── claude/default.yaml
│           └── codex/default.yaml
└── tools/
    ├── claude/
    │   ├── adapter.yaml
    │   └── setups/default/settings.json
    └── codex/
        ├── adapter.yaml
        └── setups/default/config.toml
```

### Output

Each run writes provider-specific artifacts under `scripts/demo/minimal-agent-launch/outputs/<provider>/`.

Important outputs:

- `workdir/.agentsys/agents/`: generated launch tree with local auth aliasing
- `runtime/`: built homes, manifests, and session artifacts
- `logs/launch.log`
- `logs/prompt.log`
- `logs/state.log`
- `logs/stop.log`
- `summary.json`

Representative observed state after a successful Claude run:

```json
{
  "availability": "available",
  "identity": {
    "agent_name": "minimal-launch-demo-claude",
    "tool": "claude",
    "transport": "headless"
  },
  "last_turn": {
    "result": "success",
    "turn_index": 1
  },
  "turn": {
    "phase": "ready"
  }
}
```

Representative observed state after a successful Codex run:

```json
{
  "availability": "available",
  "identity": {
    "agent_name": "minimal-launch-demo-codex",
    "tool": "codex",
    "transport": "headless"
  },
  "last_turn": {
    "result": "success",
    "turn_index": 1
  },
  "turn": {
    "phase": "ready"
  }
}
```

## Verification

- Run: `scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider claude_code`
- Run: `scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider codex`
- Confirm:
  - `scripts/demo/minimal-agent-launch/outputs/claude_code/logs/state.log` contains `"availability": "available"` and `"tool": "claude"`
  - `scripts/demo/minimal-agent-launch/outputs/codex/logs/state.log` contains `"availability": "available"` and `"tool": "codex"`
  - both `logs/stop.log` files report `"success": true`
  - the generated workdirs contain `tools/<tool>/auth/default` as a symlink to the expected fixture auth bundle

## Appendix

### Troubleshooting

- `fixture auth bundle missing`: restore the local bundle under `tests/fixtures/agents/tools/<tool>/auth/...` before running the demo
- `required command not found: claude|codex|tmux`: install the missing provider CLI or `tmux`
- Codex websocket or endpoint errors: make sure the generated Codex setup points at the Yunwu-compatible provider config and that the `yunwu-openai` fixture auth bundle is the source for the demo-local `default` alias
- `No local managed agent matched friendly name ...`: this usually means you inspected state after the script had already reached the stop step; rerun the script or inspect `logs/state.log`

### Key parameters

| Name | Meaning | Value used by this tutorial |
|---|---|---|
| `role` | Shared role selector | `minimal-launch` |
| `providers` | Supported launch providers | `claude_code`, `codex` |
| `preset auth` | Demo-local preset auth alias | `default` |
| `prompt_mode` | Headless prompt posture | `unattended` |
| `output root` | Generated run artifacts | `scripts/demo/minimal-agent-launch/outputs/<provider>/` |

## References

- Docs: [docs/getting-started/agent-definitions.md](../../../docs/getting-started/agent-definitions.md)
- Docs: [docs/getting-started/quickstart.md](../../../docs/getting-started/quickstart.md)
- Source: [tests/fixtures/agents/README.md](../../../tests/fixtures/agents/README.md)
- Source: [component-agent-construction/spec.md](../../../openspec/specs/component-agent-construction/spec.md)
