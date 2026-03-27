# Quickstart

This guide walks through the preset-backed workflow:

1. copy an `agents/` source tree
2. add local auth bundles
3. optionally build a runtime home
4. launch a managed agent

## Prerequisites

- Python 3.11+
- [Pixi](https://pixi.sh/)
- A supported CLI tool installed (`claude`, `codex`, or `gemini`)
- Local auth material for the tool you want to use

```bash
pixi install && pixi shell
```

## Step 1: Set Up `.agentsys/agents`

```bash
mkdir -p .agentsys
cp -r tests/fixtures/agents/ .agentsys/agents/
```

The canonical layout is now:

- `skills/<skill>/`
- `roles/<role>/system-prompt.md`
- `roles/<role>/presets/<tool>/<setup>.yaml`
- `tools/<tool>/adapter.yaml`
- `tools/<tool>/setups/<setup>/`
- `tools/<tool>/auth/<auth>/`

## Step 2: Add Your Local Auth Bundle

```bash
# Claude
mkdir -p .agentsys/agents/tools/claude/auth/default/env
printf 'ANTHROPIC_API_KEY=your-api-key-here\n' > .agentsys/agents/tools/claude/auth/default/env/vars.env

# Codex
mkdir -p .agentsys/agents/tools/codex/auth/default/env
printf 'OPENAI_API_KEY=your-api-key-here\n' > .agentsys/agents/tools/codex/auth/default/env/vars.env
```

## Step 3: Build A Brain Home

Using a preset:

```bash
pixi run houmao-mgr brains build \
  --agent-def-dir .agentsys/agents \
  --preset .agentsys/agents/roles/gpu-kernel-coder/presets/claude/default.yaml
```

Using explicit inputs:

```bash
pixi run houmao-mgr brains build \
  --agent-def-dir .agentsys/agents \
  --tool claude \
  --setup default \
  --auth default \
  --skill openspec-apply-change \
  --skill openspec-verify-change
```

Key options:

| Option | Description |
|---|---|
| `--preset` | Path to a preset YAML file |
| `--tool` | CLI tool name |
| `--setup` | Checked-in setup bundle |
| `--auth` | Local auth bundle |
| `--skill` | Skill name to include |
| `--runtime-root` | Optional runtime root |
| `--home-id` | Optional fixed runtime-home id |
| `--reuse-home` | Allow reuse of an existing home id |

## Step 4: Launch A Managed Agent

Launch from a bare role selector:

```bash
pixi run houmao-mgr agents launch \
  --agents gpu-kernel-coder \
  --provider claude_code \
  --agent-name research
```

The bare selector plus provider resolves:

- `gpu-kernel-coder` + `claude_code`
- to `roles/gpu-kernel-coder/presets/claude/default.yaml`

Launch a non-default setup by passing the preset path directly:

```bash
pixi run houmao-mgr agents launch \
  --agents .agentsys/agents/roles/gpu-kernel-coder/presets/codex/yunwu-openai.yaml \
  --provider codex \
  --agent-name research-codex
```

Override auth at launch time when needed:

```bash
pixi run houmao-mgr agents launch \
  --agents gpu-kernel-coder \
  --provider claude_code \
  --auth kimi-coding
```

## Step 5: Prompt And Stop

```bash
pixi run houmao-mgr agents prompt \
  --agent-name research \
  --prompt "Explain the architecture of this project."

pixi run houmao-mgr agents stop --agent-name research
```

## Next

- [Architecture Overview](overview.md)
- [Agent Definition Directory](agent-definitions.md)
