# Agents & Brains

This repo uses a **brain-first + role-first** model for running CLI agents:

- **Brains** are tool-specific runtime homes constructed from reusable components.
- **Roles** are brain-agnostic system prompts (plus optional supporting files).

The canonical on-disk sources live under an **agent definition directory** that
contains `brains/`, `roles/`, and `blueprints/`. The generated runtime homes
live under a runtime root (default: `tmp/agents-runtime/`) and are safe to
delete/rebuild.

## Canonical Layout

```text
<agent-def-dir>/
  brains/
    tool-adapters/                  # Per-tool home layout + launch rules
    cli-configs/<tool>/<profile>/   # Secret-free tool config profiles
    skills/<skill>/SKILL.md         # Reusable skills (Agent Skills format)
    brain-recipes/<tool>/*.yaml     # Declarative presets (secret-free)
    api-creds/<tool>/<profile>/...  # Local-only creds (gitignored)
  roles/
    <role>/system-prompt.md
  blueprints/
    <agent>.yaml
```

## Build A Fresh Runtime Home

The builder constructs a fresh runtime home from:

1. `tool`
2. `skills[]`
3. `config_profile`
4. `credential_profile`

### From A Recipe

```bash
pixi run python scripts/agents/build_brain_home.py \
  --agent-def-dir tests/fixtures/agents \
  --recipe brains/brain-recipes/codex/gpu-kernel-coder-default.yaml
```

### From Explicit Inputs

```bash
pixi run python scripts/agents/build_brain_home.py \
  --agent-def-dir tests/fixtures/agents \
  --tool codex \
  --skill openspec-apply-change \
  --skill openspec-verify-change \
  --config-profile default \
  --cred-profile personal-a-default
```

Outputs:

- Runtime home: `tmp/agents-runtime/homes/<tool>/<home-id>/`
- Manifest: `tmp/agents-runtime/manifests/<tool>/<home-id>.yaml`
- Launch helper: `tmp/agents-runtime/homes/<tool>/<home-id>/launch.sh`

The manifest is **secret-free** (it records env var names and local paths, but
not secret values).

## Credential Profiles (Local-Only)

Credential profiles live under:

```text
<agent-def-dir>/brains/api-creds/<tool>/<cred-profile>/
  files/...
  env/vars.env
```

This directory is **gitignored**. Do not commit secrets.

Tool notes (current adapters):

- `codex`
  - Home selector: `CODEX_HOME=<runtime-home>`
  - Credential file: `files/auth.json` (projected into the runtime home).
  - Env vars: allowlisted keys from `env/vars.env` are projected into the home
    dotenv file (see `brains/tool-adapters/codex.yaml`).
- `claude`
  - Home selector: `CLAUDE_CONFIG_DIR=<runtime-home>`
  - Local-only template input: `files/claude_state.template.json` projected to
    `<runtime-home>/claude_state.template.json` for launch-time materialization
    of `<runtime-home>/.claude.json`.
  - Config profile should include `settings.json` with
    `skipDangerousModePermissionPrompt: true`.
  - Credentials: use env vars (`ANTHROPIC_API_KEY`, etc) in `env/vars.env`, or
    use `claude auth login` outside this system if you prefer first-party auth.
  - Model selection: set `ANTHROPIC_MODEL` (plus optional vars like
    `ANTHROPIC_SMALL_FAST_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL`, and
    `ANTHROPIC_DEFAULT_*_MODEL` alias pins) in `env/vars.env` or the caller
    environment (see
    [Brain Launch Runtime](brain_launch_runtime.md#model-selection-claude-code)).
- `gemini`
  - Home selector: `GEMINI_CLI_HOME=<runtime-home>`
  - OAuth creds file: `files/oauth_creds.json` (projected to
    `<runtime-home>/.gemini/oauth_creds.json`).
  - Config/skills live under `<runtime-home>/.gemini/`.

## Launch

After building, start the tool using the generated helper:

```bash
tmp/agents-runtime/homes/<tool>/<home-id>/launch.sh
```

The helper:

- exports the tool home selector env var (from the tool adapter), and
- applies only allowlisted credential env vars (from the tool adapter + `vars.env`).
- for Claude homes, runs shared Claude bootstrap validation/materialization
  before executing `claude`.

## Roles

Roles live under `roles/<role>/system-prompt.md`.

Today, roles are applied manually (copy/paste as the first prompt) unless the
tool provides a native system/developer prompt injection mechanism.

For repo-owned session lifecycle workflows (build/start/resume/stop, including
CAO-backed sessions), use the [Brain Launch Runtime](brain_launch_runtime.md)
module and CLI.

## Programmatic Use (Python)

```python
from pathlib import Path

from gig_agents.agents import BuildRequest, build_brain_home

result = build_brain_home(
    BuildRequest(
        agent_def_dir=Path("."),
        runtime_root=Path("tmp/agents-runtime"),
        tool="codex",
        skills=["openspec-apply-change"],
        config_profile="default",
        credential_profile="personal-a-default",
    )
)

print(result.home_path)
print(result.manifest_path)
```
