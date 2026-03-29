---
tutorial_name: minimal-agent-launch
created_at: 2026-03-28T10:45:10Z
base_commit: ceea9c3272c19ac91464ab4d2cca77cb81697a8a
topic: Houmao - Minimal Agent Launch Demo
runtime:
  os: Linux
  python: 3.13.12
  device: cpu
  notes: Claude and Codex were verified across both default TUI and `--headless` lanes against the local fixture auth bundles under tests/fixtures/agents/tools.
---

# How to launch one minimal Houmao agent across Claude/Codex and TUI/headless

## Question

How do I define the smallest canonical `agents/` tree that can launch one managed agent through Houmao, keep auth local-only, and still support both Claude and Codex with TUI as the default and `--headless` as the headless switch?

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

At run time, the script copies those tracked inputs into a generated workdir, creates a demo-local `default` auth symlink for the selected provider, points Houmao at that generated `agents/` tree, and then chooses one of two flows:

- default TUI: `launch -> state`, then leaves the agent alive and reports the tmux attach handoff for follow-up control
- `--headless`: `launch -> prompt -> state -> stop`

## Critical Example Code

### Bash

```bash
provider="codex"  # or claude_code
headless="false"  # set to true for the headless lane
tool="codex"

if [[ "${headless}" == "true" ]]; then
  run_root="scripts/demo/minimal-agent-launch/outputs/${provider}-headless"
  agent_name="minimal-launch-demo-${tool}-headless"
else
  run_root="scripts/demo/minimal-agent-launch/outputs/${provider}"
  agent_name="minimal-launch-demo-${tool}"
fi

generated_agent_def_dir="${run_root}/workdir/.houmao/agents"

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

launch_args=(
  pixi run houmao-mgr agents launch
  --agents minimal-launch
  --provider "${provider}"
  --agent-name "${agent_name}"
  --yolo
)
if [[ "${headless}" == "true" ]]; then
  launch_args+=(--headless)
fi

AGENTSYS_AGENT_DEF_DIR="$PWD/${generated_agent_def_dir}" \
AGENTSYS_GLOBAL_RUNTIME_DIR="$PWD/${run_root}/runtime" \
"${launch_args[@]}"
```

For the full runnable flow, use the tracked script instead of retyping the steps:

```bash
scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider claude_code
scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider claude_code --headless
scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider codex
scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider codex --headless
```

## Input and Output

### Input

The tracked demo inputs are:

- `inputs/agents/roles/minimal-launch/system-prompt.md`: one shared role prompt
- `inputs/agents/roles/minimal-launch/presets/claude/default.yaml`: minimal Claude preset
- `inputs/agents/roles/minimal-launch/presets/codex/default.yaml`: minimal Codex preset
- `inputs/agents/tools/claude/...`: secret-free Claude adapter and setup
- `inputs/agents/tools/codex/...`: secret-free Codex adapter and setup
- `inputs/prompt.txt`: the prompt submitted after a headless launch

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

Each run writes generated artifacts under a lane-specific root:

- default Claude TUI: `outputs/claude_code/`
- Claude headless: `outputs/claude_code-headless/`
- default Codex TUI: `outputs/codex/`
- Codex headless: `outputs/codex-headless/`

Important generated outputs for every lane:

- `workdir/.houmao/agents/`: generated launch tree with the demo-local auth alias
- `runtime/`: built homes, manifests, and session artifacts
- `logs/preflight-stop.log`: best-effort cleanup of a stale agent with the same demo name
- `logs/launch.log`
- `logs/state.log`
- `summary.json`

Headless-only generated outputs:

- `logs/prompt.log`
- `logs/stop.log`

Representative observed headless state:

```json
{
  "availability": "available",
  "identity": {
    "agent_name": "minimal-launch-demo-codex-headless",
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

Representative observed default TUI state:

```json
{
  "availability": "available",
  "identity": {
    "agent_name": "minimal-launch-demo-claude",
    "tool": "claude",
    "transport": "tui"
  },
  "last_turn": {
    "result": "none",
    "turn_index": null
  },
  "turn": {
    "phase": "ready"
  }
}
```

Representative observed non-interactive TUI handoff:

```text
terminal_handoff=skipped_non_interactive
attach_command=tmux attach-session -t AGENTSYS-minimal-launch-demo-claude-1774696208764
```

## Verification

Run each supported lane:

- `scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider claude_code`
- `scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider claude_code --headless`
- `scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider codex`
- `scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider codex --headless`

Observed verification results on 2026-03-28:

| Lane | Output root | Observed launch/state evidence |
|---|---|---|
| Claude TUI | `outputs/claude_code/` | `agent_name=minimal-launch-demo-claude`, `tool=claude`, `transport=tui`, `turn.phase=ready`, `terminal_handoff=skipped_non_interactive`, `attach_command=tmux attach-session -t AGENTSYS-minimal-launch-demo-claude-1774696208764` |
| Claude headless | `outputs/claude_code-headless/` | `agent_name=minimal-launch-demo-claude-headless`, `tool=claude`, `transport=headless`, `last_turn.result=success`, `logs/stop.log` reported `"success": true` |
| Codex TUI | `outputs/codex/` | `agent_name=minimal-launch-demo-codex`, `tool=codex`, `transport=tui`, `turn.phase=ready`, `terminal_handoff=skipped_non_interactive`, `attach_command=tmux attach-session -t AGENTSYS-minimal-launch-demo-codex-1774696235259` |
| Codex headless | `outputs/codex-headless/` | `agent_name=minimal-launch-demo-codex-headless`, `tool=codex`, `transport=headless`, `last_turn.result=success`, `logs/stop.log` reported `"success": true` |

What to confirm after a run:

- `summary.json` records the selected `provider`, derived `transport`, and fixture auth source
- `logs/state.log` contains `"availability": "available"` with the expected `tool` and `transport`
- headless lanes write both `logs/prompt.log` and `logs/stop.log`
- default TUI lanes leave the agent alive and publish `tmux_session_name`, `terminal_handoff`, and `attach_command`
- the generated workdir contains `tools/<tool>/auth/default` as a symlink to the expected fixture auth bundle

## Appendix

### Troubleshooting

- `fixture auth bundle missing`: restore the local bundle under `tests/fixtures/agents/tools/<tool>/auth/...` before running the demo
- `required command not found: claude|codex|tmux`: install the missing provider CLI or `tmux`
- Codex websocket or endpoint errors: make sure the generated Codex setup points at the Yunwu-compatible provider config and that the `yunwu-openai` fixture auth bundle is the source for the demo-local `default` alias
- `No local managed agent matched friendly name ...` in `preflight-stop.log`: this is expected on a first run or after a clean stop, because the runner always attempts best-effort cleanup before launch
- Default TUI lanes from non-interactive shells intentionally do not attach automatically; expect `terminal_handoff=skipped_non_interactive` and use the returned `attach_command`
- TUI lanes remain running after the script exits; stop them explicitly when you are done, for example `pixi run houmao-mgr agents stop --agent-name minimal-launch-demo-claude` or `pixi run houmao-mgr agents stop --agent-name minimal-launch-demo-codex`
- Headless lanes stop themselves before the script exits, so a follow-up `agents state` lookup by friendly name may fail unless you rerun the lane and inspect `logs/state.log`

### Key parameters

| Name | Meaning | Value used by this tutorial |
|---|---|---|
| `role` | Shared role selector | `minimal-launch` |
| `providers` | Supported launch providers | `claude_code`, `codex` |
| `default transport` | Launch mode when `--headless` is absent | `tui` |
| `headless switch` | Explicit headless selector | `--headless` |
| `preset auth` | Demo-local preset auth alias | `default` |
| `output root` | Generated run artifacts | `scripts/demo/minimal-agent-launch/outputs/<provider>[-headless]/` |

## References

- Docs: [docs/getting-started/agent-definitions.md](../../../docs/getting-started/agent-definitions.md)
- Docs: [docs/getting-started/quickstart.md](../../../docs/getting-started/quickstart.md)
- Source: [tests/fixtures/agents/README.md](../../../tests/fixtures/agents/README.md)
- Source: [component-agent-construction/spec.md](../../../openspec/specs/component-agent-construction/spec.md)
