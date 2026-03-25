# Houmao
> A framework and CLI toolkit for orchestrating teams of loosely-coupled AI agents.

## Current Status

### Development State

Houmao is under active development, and the operator-facing workflow is still stabilizing. Expect rough edges, incomplete coverage, and interface changes while the core runtime, gateway, and mailbox contracts continue to harden.

### Current Proof Of Concept

The current end-to-end proof-of-concept is the headless ping-pong demo pack at `scripts/demo/mail-ping-pong-gateway-demo-pack/`. It launches one headless Claude agent and one headless Codex agent, lets them coordinate through the shared mailbox and gateway surfaces, and verifies the resulting conversation from demo-owned artifacts.

### Current Limitations

- **Headless only:** the demo uses headless calls, so the operator does not get an in-band interactive user surface during the run.
- **Raw artifact viewing:** its primary outputs are raw JSON inspect/report artifacts, which are good for verification but not yet a polished human-facing viewing experience.

### Recommended First Run

If you want to try Houmao today, start by following that demo instead of assembling a custom workflow from scratch. Treat its practice as the current recommended path:

- use a tracked agent-definition directory with recipes, roles, and projected runtime-owned skills
- keep generated runtime, mailbox, project, and server state under one dedicated output root
- drive the system through the managed `start -> kickoff -> wait/inspect -> verify -> stop` flow
- use the persisted inspect and report artifacts as the source of truth for what happened
- prefer the gateway-first shared mailbox workflow demonstrated there for multi-agent coordination

Once that demo works in your environment, use it as the baseline pattern for adapting Houmao to your own agents and tasks.

### Watching The Demo

Even though the ping-pong proof-of-concept is headless, the started agent processes are still tmux-backed diagnostic surfaces.

- Run `scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh inspect --demo-output-dir <output-root>` to refresh the persisted state.
- Read `control/demo_state.json` under that output root to find each participant's `tmux_session_name`.
- Attach directly with `tmux attach -t <tmux_session_name>` and watch window `0` (`agent`) for the live CLI output.
- For web-based viewing, prefer `tailmux` pointed at those same tmux sessions instead of reading the raw JSON files by hand.

## Project Introduction

### What It Is

`Houmao` is a framework and CLI toolkit designed to orchestrate **teams of loosely-coupled, CLI-based AI agents**.

> **Name Origin:** `Houmao` (猴毛, "monkey hair") is inspired by the classic tale *Journey to the West*. Just as Sun Wukong (The Monkey King) plucks strands of his magical hair to create independent, capable clones of himself, this framework allows you to multiply your capabilities by spinning up numerous autonomous helpers.

Unlike traditional orchestration models where an "agent" is merely an in-process object graph, `Houmao` treats each agent as a first-class citizen. Every agent is a dedicated, real CLI process (such as `codex`, `claude`, or `gemini`) operating with its own isolated disk state, memory, and native user experience.

### The Core Idea (What We Avoid)

The core idea is to **avoid a hard-coded orchestration model**.

Instead of shipping a fixed “agent graph” runtime (LangGraph / AutoGen-style orchestration), `Houmao` treats a team as a set of **independently runnable CLI agents** and provides lightweight primitives to construct, start, and manage them, while keeping “how the team coordinates” **flexible and context-driven**.

> Note
> Today, the primary construction paradigm is an **agent definition directory** (brains + roles + optional blueprints).
> The details of “tool specs vs skills vs roles” are implementation choices that may evolve; the stable goal is **maximum flexibility with real, inspectable CLI agent processes**.

### What The Framework Provides

- **Construction**: build agent runtimes from tool specs + skills + roles (and optional blueprints).
- **Management**: start/resume/prompt/stop agents with `houmao-cli` (typically tmux-backed so you can inspect and interact).
- **Team communication**: a shared control/communication plane for groups of terminals (currently built on CAO internally, optional).

### Why This Is Useful (Benefits)

- **Low barrier to composition**: assemble new agent teams from human-like instruction packages (skills + roles) and tool profiles, without designing rigid contracts up front.
- **Flexible team contracts**: coordination choices can change with context because the framework does not impose a fixed graph or flow.
- **Transparent per-agent UX**: each agent is a real CLI process; you can attach to its tmux window/session to see what it’s doing and interact with its native TUI when needed.
- **Full tool surface area**: the system operates the same terminal/TUI interface you do, so every native capability remains usable (and you can always take over manually if automation hits an unexpected prompt).

### Typical Use Cases

- **Parallel specialist agents**: run a "coder" agent and a "reviewer" agent side by side on the same repo — each with a different role and tool — so one writes while the other critiques.
- **Optimization loops**: set up a coder agent that implements changes and a profiler agent that benchmarks them, iterating back and forth without manual handoff.
- **Team agent presets**: give every team member the same pre-configured agent lineup (same models, skills, and roles) checked into the repo, without sharing anyone's API keys.
- **Swap the AI, keep the workflow**: change which model or CLI tool an agent uses without touching its role prompt or the task it is working on.

### How Agents Join Your Workflow

- **Managed launch (recommended):** construct from tool specs + skills + roles/blueprints, then start/resume/prompt/stop via `houmao-cli`.
- **Bring-your-own process:** you can also start the underlying CLI tool manually (for example via the generated `launch_helper_path` from `build-brain`) and still participate in the same “agent team” workflow. First-class adoption/attach of an already-running tmux session is a design goal; today, the management commands assume the session was launched by `houmao-cli`.

## Installation

Pixi (recommended):

```bash
pixi install
pixi shell
```

Optional Postgres + pgvector environment (for future context hosting):

- Intended future use: manage persistent agent context such as RAG knowledge bases, dialog history, and work artifacts.
- Not required for current core runtime flows.

```bash
pixi install -e pg-hosting --manifest-path pyproject.toml
pixi run -e pg-hosting pg-init
```

Or editable install:

```bash
pip install -e .
```

### CAO (optional)

CAO is an internal dependency for Houmao's CAO-backed paths. Install it if you want to use the `cao_rest` backend, `houmao-cao-server`, or the `houmao-server + houmao-mgr` replacement pair.

In normal operator workflows, prefer the Houmao utilities over invoking raw `cao` or `cao-server` directly. Houmao still depends on CAO internally for the `cao_rest` backend and CAO-compatible control surfaces.

Install CAO from the pinned compatibility commit used by this repository:

```bash
uv tool install --upgrade git+https://github.com/imsight-forks/cli-agent-orchestrator.git@0fb3e5196570586593736a21262996ca622f53b6
```

Verify the required executables are available:

```bash
command -v cao-server
command -v tmux
```

## Usage Guide

### CLI Entry Points

- `houmao-cli`: build/start/prompt/stop lifecycle
- `houmao-cao-server`: local `cao-server` start/status/stop (optional)
- `houmao-server`: Houmao-owned CAO-compatible server with Houmao extension routes
- `houmao-mgr`: Pair-management CLI paired with `houmao-server`

Prefer these Houmao entry points for normal use. Raw `cao` and `cao-server` are still part of the underlying dependency stack, but they are not the recommended primary interface for Houmao workflows.

```bash
houmao-cli --help
houmao-cao-server --help
houmao-server --help
houmao-mgr --help
```

### 1. Create / Choose An Agent Definition Directory

An **agent definition directory** is any folder (name is not hard-coded) that contains `brains/`, `roles/`, and optionally `blueprints/`.

Commands that need agent definitions resolve the directory with this precedence:

1. CLI `--agent-def-dir`
2. env `AGENTSYS_AGENT_DEF_DIR`
3. default `<pwd>/.agentsys/agents`

This repo includes a complete template you can copy and customize:

```bash
mkdir -p .agentsys
cp -a tests/fixtures/agents .agentsys/agents
export AGENTSYS_AGENT_DEF_DIR="$PWD/.agentsys/agents"
```

Then replace the credential profiles under `brains/api-creds/` with your own (keep them uncommitted).

### 2. Prepare The Agent Definition Directory Contents

Top-level purpose summary:

- `brains/`: reusable building blocks for constructing runtime homes.
- `roles/`: role prompt packages that define agent behavior/policy for a session.
- `blueprints/`: optional presets that bind a recipe to a role.

Within `brains/`:

- `tool-adapters/`: per-tool build/launch contract.
- `skills/`: reusable capabilities; each agent selects a subset.
- `cli-configs/`: secret-free tool config profiles.
- `api-creds/`: local-only credential profiles (gitignored).
- `brain-recipes/`: secret-free presets for tool + skill subset + profiles.

```text
<agent-def-dir>/
  brains/
    tool-adapters/                     # REQUIRED: one `<tool>.yaml` per supported tool
    skills/<skill-name>/SKILL.md       # REQUIRED (per recipe): reusable skill packages
    cli-configs/<tool>/<profile>/...   # REQUIRED (per recipe): secret-free tool config profiles
    api-creds/<tool>/<profile>/...     # REQUIRED (per recipe): local-only credential profiles (gitignored)
    brain-recipes/<tool>/*.yaml        # OPTIONAL: secret-free presets (recommended)
  roles/<role>/system-prompt.md        # REQUIRED: role prompt packages
  blueprints/*.yaml                    # OPTIONAL: recipe+role bindings (recommended)
```

#### `brains/tool-adapters/` (required)

Tool adapters are the per-tool contract between your source tree and the generated runtime home.

- Purpose: define how `build-brain` materializes a runnable home for each tool (`codex`, `claude`, `gemini`).
- Launch definition: executable, default args, and home selector env var (for example `CODEX_HOME`).
- Projection rules: where selected `cli-configs/`, `skills/`, and credential files land inside the runtime home.
- Credential env policy: which keys from `env/vars.env` are allowlisted and how they are injected at launch.

For the full adapter model and end-to-end behavior, see [Agents & Brains](docs/reference/agents_brains.md).

#### `brains/skills/` (required by recipes)

Skills are reusable capability modules (each with a `SKILL.md` entrypoint) that recipes select from.

- Purpose: define composable behaviors and workflows that can be mixed per agent.
- Agent shaping: each agent selects a subset of available skills, and that selected subset is what makes the resulting agent role-specific in practice.

Skill example (`tests/fixtures/agents/brains/skills/openspec-apply-change/SKILL.md`):

```markdown
---
name: openspec-apply-change
description: Implement tasks from an OpenSpec change.
---

Implement tasks from an OpenSpec change.
```

#### `brains/cli-configs/` (required by recipes, secret-free)

Tool-specific config profiles that the builder projects into the constructed runtime home.

Codex default profile example (`tests/fixtures/agents/brains/cli-configs/codex/default/config.toml`):

```toml
model = "gpt-5.3-codex"
model_reasoning_effort = "high"
personality = "friendly"
```

Claude default profile example (`tests/fixtures/agents/brains/cli-configs/claude/default/settings.json`):

```json
{
  "skipDangerousModePermissionPrompt": true
}
```

#### `brains/api-creds/` (required by recipes, local-only)

Credential profiles must stay uncommitted. Use a `files/` directory plus an `env/vars.env` file.

Template layout example:

```text
brains/api-creds/codex/personal-a-default/
  files/auth.json
  env/vars.env
```

`vars.env` example (`tests/fixtures/agents/brains/api-creds/codex/personal-a-default/env/vars.env`):

```bash
# OPENAI_API_KEY=<unset>
# OPENAI_BASE_URL=<unset>
# OPENAI_ORG_ID=<unset>
```

Keep real credential files (like `files/auth.json`) local-only and gitignored.

#### `brains/brain-recipes/` (recommended, secret-free)

Recipes are declarative presets selecting tool + skill subset + config profile + credential profile.

Example recipe (`tests/fixtures/agents/brains/brain-recipes/codex/gpu-kernel-coder-default.yaml`):

```yaml
schema_version: 1
name: gpu-kernel-coder-default
tool: codex
skills:
  - openspec-apply-change
  - openspec-verify-change
config_profile: default
credential_profile: personal-a-default
```

#### `roles/` (required)

Each role is a package directory with a required `system-prompt.md` (and optional `files/`).

Role prompt excerpt (`tests/fixtures/agents/roles/gpu-kernel-coder/system-prompt.md`):

```markdown
# SYSTEM PROMPT: GPU KERNEL CODER

You are the coding worker in a GPU kernel optimization loop.
You implement bounded CUDA/C++ changes, run validation, and report reproducible results.
```

#### `blueprints/` (recommended, secret-free)

Blueprints bind a brain recipe to a role without embedding credentials.

Example blueprint (`tests/fixtures/agents/blueprints/gpu-kernel-coder.yaml`):

```yaml
schema_version: 1
name: gpu-kernel-coder
brain_recipe: ../brains/brain-recipes/codex/gpu-kernel-coder-default.yaml
role: gpu-kernel-coder
```

### 3. Basic Workflow (Local tmux)

Build a brain home:

```bash
houmao-cli build-brain \
  --recipe brains/brain-recipes/codex/gpu-kernel-coder-default.yaml \
  --runtime-root tmp/agents-runtime
```

Output is JSON including `home_path`, `manifest_path`, and `launch_helper_path`.

Manual start option: if you want to run the tool yourself (outside `start-session`), execute the returned `launch_helper_path` inside your own tmux/window. Managed lifecycle commands (`send-prompt`, `stop-session`) require a session started by `houmao-cli`.

Start a session and send a prompt:

```bash
houmao-cli start-session \
  --brain-manifest <manifest-path-from-build-output> \
  --role gpu-kernel-coder \
  --agent-identity my-agent

houmao-cli send-prompt \
  --agent-identity my-agent \
  --prompt "Review the latest commit for security issues"

houmao-cli stop-session --agent-identity my-agent
```

### 4. Blueprint-Driven Preset (Recipe + Role)

```bash
houmao-cli build-brain --blueprint blueprints/gpu-kernel-coder.yaml

houmao-cli start-session \
  --brain-manifest <manifest-path-from-build-output> \
  --blueprint blueprints/gpu-kernel-coder.yaml
```

### 5. CAO-Backed Sessions (Optional)

Prefer the Houmao launcher wrapper when you need a local CAO-compatible control plane:

```bash
houmao-cao-server start  --config config/cao-server-launcher/local.toml
houmao-cao-server status --config config/cao-server-launcher/local.toml
houmao-cao-server stop   --config config/cao-server-launcher/local.toml
```

For a one-off local port override, add `--base-url http://127.0.0.1:9991`.

Start a session through CAO:

```bash
houmao-cli start-session \
  --brain-manifest <manifest-path-from-build-output> \
  --role gpu-kernel-coder \
  --backend cao_rest \
  --cao-base-url http://localhost:9889
```

Supported local CAO URLs use `http://localhost:<port>` or
`http://127.0.0.1:<port>`.

## Developer Guide

### Architecture

```mermaid
flowchart TB
    subgraph agentdef ["Agent Definition Directory"]
        adapter["Tool Adapter<br/>per-tool build & launch rules"]
        recipe["Brain Recipe<br/>tool + skills + config & cred profiles"]
        role["Role<br/>system prompt package"]
        blueprint["Blueprint  (optional)<br/>recipe + role binding"]
    end

    subgraph buildphase ["① Build Phase"]
        builder["Brain Builder"]
        artifact["Brain Manifest<br/>& Runtime Home"]
        builder --> artifact
    end

    subgraph runphase ["② Run Phase"]
        runtime["Session Driver"]
        subgraph backends ["Launch Backend  (pick one)"]
            direction LR
            tmux_b["tmux<br/>(local)"]
            cao_b["CAO REST<br/>(optional)"]
        end
        toolcli["Tool CLI Process<br/>codex · claude · gemini"]
        runtime --> tmux_b & cao_b --> toolcli
    end

    extcao(["CAO Server<br/>(optional external)"])
    caocli["houmao-cao-server"]
    agentscli["houmao-cli<br/>build · start · prompt · stop"]

    %% Build inputs
    adapter --> builder
    recipe --> builder
    blueprint -. "shorthand: recipe + role" .-> builder

    %% Phase handoff
    artifact --> runtime
    role --> runtime
    blueprint -. "role ref" .-> runtime

    %% CAO path
    cao_b <--> extcao
    caocli --> extcao

    %% CLI orchestrates both phases
    agentscli --> builder
    agentscli --> runtime
```

### Sequence (UML)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant CLI as houmao-cli
    participant Builder as Brain builder
    participant Runtime as Runtime
    participant TMUX as tmux
    participant CAO as CAO (optional)
    participant Tool as Tool CLI

    User->>CLI: build-brain (--recipe / --blueprint)
    CLI->>Builder: load agent-def-dir + inputs
    Builder-->>CLI: manifest_path (plus home_path)

    User->>CLI: start-session (--brain-manifest, --role/--blueprint)
    CLI->>Runtime: launch session

    alt Local tmux backend
        Runtime->>TMUX: create session/window
        Runtime->>Tool: exec tool under tmux
    else CAO backend
        Runtime->>CAO: create session + terminal
        Runtime->>Tool: exec tool under CAO-managed tmux
    end

    User->>CLI: send-prompt (--agent-identity)
    CLI->>Runtime: submit prompt
    Runtime-->>CLI: structured turn result

    User->>CLI: stop-session (--agent-identity)
    CLI->>Runtime: stop/cleanup
```

### Development Checks

```bash
pixi run format
pixi run lint
pixi run typecheck
pixi run test-runtime
```

## Appendix

### CAO

CAO (CLI Agent Orchestrator) provides the REST session/terminal control plane used internally by the `cao_rest` backend and by Houmao's CAO-compatible launcher or server flows.
It also exposes an inbox messaging API that can be used as a communication channel between agents/terminals.

For normal Houmao usage, prefer `houmao-cao-server`, `houmao-server`, and `houmao-mgr` instead of invoking raw `cao` or `cao-server` directly. Direct CAO invocation is mainly useful when debugging the underlying dependency or validating behavior below Houmao's wrappers.

Install CAO from the supported fork / pinned compatibility commit and verify required executables are on `PATH`. We recommend the fork because `Houmao` may depend on CAO features that are not yet present on upstream `main`:

```bash
uv tool install --upgrade git+https://github.com/imsight-forks/cli-agent-orchestrator.git@0fb3e5196570586593736a21262996ca622f53b6
command -v cao-server
command -v tmux
```

Primary CAO links:

- Supported fork: <https://github.com/imsight-forks/cli-agent-orchestrator/tree/hz-release>
- Fork README (install + usage): <https://github.com/imsight-forks/cli-agent-orchestrator/tree/hz-release#readme>
- Original upstream project: <https://github.com/awslabs/cli-agent-orchestrator>
