# Quickstart

This guide walks you through building an agent brain and running an interactive session using `houmao-mgr`. By the end, you will have a working agent you can send prompts to and terminate cleanly.

```mermaid
sequenceDiagram
    participant Op as Operator
    participant Mgr as houmao-mgr
    participant BB as BrainBuilder
    participant RT as RuntimeSession<br/>Controller
    participant BE as Backend<br/>(tmux)

    Op->>Mgr: brains build<br/>(recipe, agent-def-dir)
    Mgr->>BB: build_brain_home()
    BB-->>Mgr: BuildResult<br/>(manifest path)
    Op->>Mgr: agents launch<br/>(manifest, role)
    Mgr->>RT: start_runtime_session()
    RT->>BE: create session
    BE-->>RT: InteractiveSession
    RT-->>Mgr: controller ready
    Op->>Mgr: agents prompt<br/>("write tests")
    Mgr->>RT: send_prompt()
    RT->>BE: paste into tmux
    BE-->>RT: session events
    RT-->>Mgr: prompt accepted
    Op->>Mgr: agents stop
    Mgr->>RT: terminate()
    RT->>BE: kill tmux session
    RT-->>Mgr: stopped
```

## Prerequisites

- Python 3.11+
- [Pixi](https://pixi.sh/) installed
- A supported CLI tool installed (`claude`, `codex`, or `gemini`)
- API credentials for your chosen tool

Install Houmao and enter the dev shell:

```bash
pixi install && pixi shell
```

## Step 1: Set Up the Agent Definition Directory

The agent definition directory contains everything Houmao needs to build and run agent brains — tool adapters, skills, configs, credentials, recipes, and roles.

Copy the template from the test fixtures:

```bash
mkdir -p .agentsys
cp -r tests/fixtures/agents/ .agentsys/agents/
```

This gives you a working directory structure with example tool adapters, skills, config profiles, recipes, and roles. See [Agent Definition Directory](agent-definitions.md) for a detailed breakdown of each component.

### Add Your Credentials

Credentials are local-only and never committed. Create the credential profile for your tool:

```bash
# For Claude
mkdir -p .agentsys/agents/brains/api-creds/claude/default/env
cat > .agentsys/agents/brains/api-creds/claude/default/env/vars.env << 'EOF'
ANTHROPIC_API_KEY=your-api-key-here
EOF

# For Codex
mkdir -p .agentsys/agents/brains/api-creds/codex/default/env
cat > .agentsys/agents/brains/api-creds/codex/default/env/vars.env << 'EOF'
OPENAI_API_KEY=your-api-key-here
EOF

# For Gemini
mkdir -p .agentsys/agents/brains/api-creds/gemini/default/env
cat > .agentsys/agents/brains/api-creds/gemini/default/env/vars.env << 'EOF'
GEMINI_API_KEY=your-api-key-here
EOF
```

## Step 2: Build a Brain

The build phase resolves a recipe against the agent definition directory and produces a runtime home with projected configs, skills, and credentials.

### Using a Recipe (Recommended)

```bash
pixi run houmao-mgr brains build \
  --agent-def-dir .agentsys/agents \
  --recipe .agentsys/agents/brains/brain-recipes/claude/default.yaml
```

### Using Explicit Parameters

If you prefer to specify each component individually instead of using a recipe:

```bash
pixi run houmao-mgr brains build \
  --agent-def-dir .agentsys/agents \
  --tool claude \
  --skill code-review \
  --skill testing \
  --config-profile default \
  --cred-profile default
```

### Build Options Reference

| Option | Description |
|---|---|
| `--agent-def-dir` | Path to the agent definition directory |
| `--recipe` | Path to a brain recipe YAML file |
| `--tool` | CLI tool name (e.g., `claude`, `codex`, `gemini`) |
| `--skill` | Skill name to include (repeatable) |
| `--config-profile` | Secret-free config profile name |
| `--cred-profile` | Local credential profile name |
| `--runtime-root` | Where to create the runtime home (default: `tmp/`) |
| `--home-id` | Explicit home ID (auto-generated if omitted) |
| `--reuse-home` | Reuse an existing runtime home instead of creating a new one |
| `--launch-overrides` | JSON string of additional launch arguments |
| `--agent-name` | Human-readable agent name |
| `--agent-id` | Unique agent identifier |

On success, the build emits the path to the generated `BrainManifest` and a launch helper script. Note the manifest path — you will need it for the next step.

## Step 3: Launch a Session

Launch an interactive agent session using the built brain:

```bash
pixi run houmao-mgr agents launch \
  --manifest <path-to-manifest.json> \
  --role default \
  --backend local_interactive
```

This starts the agent CLI inside a tmux session. The `local_interactive` backend gives you a fully interactive tmux-backed process.

For headless (programmatic) use, choose the appropriate backend:

```bash
# Claude headless
pixi run houmao-mgr agents launch \
  --manifest <path-to-manifest.json> \
  --role default \
  --backend claude_headless

# Codex headless
pixi run houmao-mgr agents launch \
  --manifest <path-to-manifest.json> \
  --role default \
  --backend codex_headless
```

## Step 4: Send a Prompt

Once a session is running, send prompts to it:

```bash
pixi run houmao-mgr agents prompt \
  --session-id <session-id> \
  --message "Explain the architecture of this project."
```

The session ID is returned when you launch the session. For headless backends, the response is returned directly. For interactive backends, the prompt is sent to the tmux session.

## Step 5: Stop the Session

Terminate a running session cleanly:

```bash
pixi run houmao-mgr agents terminate --session-id <session-id>
```

This stops the agent CLI process and cleans up the tmux session (for interactive backends).

## End-to-End Example

Here is the full workflow for building and running a Claude agent:

```bash
# 1. Build the brain
pixi run houmao-mgr brains build \
  --agent-def-dir .agentsys/agents \
  --recipe .agentsys/agents/brains/brain-recipes/claude/default.yaml

# Note the manifest path from the output, e.g.:
#   Manifest written to: tmp/homes/<home-id>/brain-manifest.json

# 2. Launch an interactive session
pixi run houmao-mgr agents launch \
  --manifest tmp/homes/<home-id>/brain-manifest.json \
  --role default \
  --backend local_interactive

# Note the session ID from the output

# 3. Send a prompt
pixi run houmao-mgr agents prompt \
  --session-id <session-id> \
  --message "Hello, what can you help me with?"

# 4. Terminate when done
pixi run houmao-mgr agents terminate --session-id <session-id>
```

## What's Next

- **[Architecture Overview](overview.md)** — Understand the two-phase lifecycle, backend model, and system architecture.
- **[Agent Definition Directory](agent-definitions.md)** — Deep dive into the directory layout, what each component does, and how they connect.
