# Agents & Brains

This repo uses a **brain-first + role-first** model for running CLI agents:

- **Brains** are tool-specific runtime homes constructed from reusable components.
- **Roles** are brain-agnostic system prompts (plus optional supporting files).

For the runtime-managed session model layered on top of these built homes, use [Runtime-Managed Agents Reference](./agents/index.md). For the optional per-session gateway sidecar, use [Agent Gateway Reference](./gateway/index.md).

The canonical on-disk sources live under an **agent definition directory** that
contains `brains/`, `roles/`, and `blueprints/`. The generated runtime homes
live under the effective runtime root (default: `~/.houmao/runtime`) and are
safe to delete or rebuild. Use [Agents And Runtime](./system-files/agents-and-runtime.md) for the canonical generated-home, manifest, and session-root filesystem map.

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

For the Yunwu-backed Codex profile:

```bash
pixi run python scripts/agents/build_brain_home.py \
  --agent-def-dir tests/fixtures/agents \
  --recipe brains/brain-recipes/codex/gpu-kernel-coder-yunwu-openai.yaml
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

Or build the Yunwu-backed Codex agent explicitly:

```bash
pixi run python scripts/agents/build_brain_home.py \
  --agent-def-dir tests/fixtures/agents \
  --tool codex \
  --skill openspec-apply-change \
  --skill openspec-verify-change \
  --config-profile yunwu-openai \
  --cred-profile yunwu-openai
```

Outputs:

- Runtime home: `<runtime-root>/homes/<home-id>/`
- Manifest: `<runtime-root>/manifests/<home-id>.yaml`
- Launch helper: `<runtime-root>/homes/<home-id>/launch.sh`

The manifest is **secret-free** (it records env var names and local paths, but
not secret values).

Both recipe-driven and explicit builds can also declare the operator-prompt posture. Use `launch_policy.operator_prompt_mode` in the recipe or pass `--operator-prompt-mode unattended` to `build-brain` when you want Houmao to resolve a versioned unattended launch strategy at runtime. The default remains `interactive`.

Both recipe-driven and explicit builds also share the same secret-free `launch_overrides` contract for optional launch behavior. Recipes can declare:

```yaml
launch_overrides:
  args:
    mode: append
    values:
      - --example-flag
  tool_params:
    include_partial_messages: true
```

Explicit builds can pass the same shape through `build-brain --launch-overrides <path-or-inline-json>`.

Ownership rules:

- Tool adapters still own `launch.executable`, adapter default args, and declarative optional-launch metadata.
- Recipes and direct builds only request secret-free overrides on top of those defaults.
- Backend-owned protocol args such as `claude -p`, `gemini -p`, `codex exec --json`, `resume`, and `app-server` stay in runtime backend code and are not recipe-overridable.
- The builder persists unresolved launch intent only; backend-specific applicability and effective args are resolved later when a session is launched.

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
  - Optional login-state file: `files/auth.json` is projected into the runtime
    home when the selected credential profile provides it. Env-backed Codex
    profiles such as `yunwu-openai` are allowed to omit `files/auth.json`
    entirely when they rely on `OPENAI_API_KEY`/`OPENAI_BASE_URL`.
  - Env vars: allowlisted keys from `env/vars.env` are projected into the home
    dotenv file (see `brains/tool-adapters/codex.yaml`).
  - Custom OpenAI-compatible providers can use a secret-free config profile such
    as `cli-configs/codex/yunwu-openai/` together with a local-only credential
    profile such as `api-creds/codex/yunwu-openai/`.
  - Launch preparation requires either a non-empty top-level JSON object in
    `auth.json` or `OPENAI_API_KEY` in the effective runtime environment.
    Placeholder `{}` files do not satisfy that requirement on their own.
- `claude`
  - Home selector: `CLAUDE_CONFIG_DIR=<runtime-home>`
  - Optional seed state: `files/claude_state.template.json` may be projected to
    `<runtime-home>/claude_state.template.json` when you want to preserve or extend existing Claude state, but unattended launches no longer require the template up front.
  - For supported unattended versions, Houmao can synthesize or patch
    `settings.json` and `.claude.json` from runtime-owned launch policy instead
    of requiring user-prepared prompt-suppression files.
  - Credentials: use env vars (`ANTHROPIC_API_KEY`, etc) in `env/vars.env`, or
    use `claude auth login` outside this system if you prefer first-party auth.
  - Model selection: set `ANTHROPIC_MODEL` (plus optional vars like
    `ANTHROPIC_SMALL_FAST_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL`, and
    `ANTHROPIC_DEFAULT_*_MODEL` alias pins) in `env/vars.env` or the caller
    environment (see
    [Realm Controller](realm_controller.md#model-selection-claude-code)).
- `gemini`
  - Home selector: `GEMINI_CLI_HOME=<runtime-home>`
  - OAuth creds file: `files/oauth_creds.json` (projected to
    `<runtime-home>/.gemini/oauth_creds.json`).
  - Config/skills live under `<runtime-home>/.gemini/`.

## Launch

After building, start the tool using the generated helper:

```bash
<runtime-root>/homes/<home-id>/launch.sh
```

Example live Codex smoke test for the Yunwu-backed profile:

```bash
<runtime-root>/homes/<home-id>/launch.sh exec --skip-git-repo-check \
  'Respond with exactly this text and nothing else: YUNWU_CODEX_SMOKE_OK'
```

Treat the profile as working only when Codex returns exactly
`YUNWU_CODEX_SMOKE_OK`.

The helper:

- exports the tool home selector env var (from the tool adapter), and
- applies only allowlisted credential env vars (from the tool adapter + `vars.env`).
- if the manifest sets `launch_policy.operator_prompt_mode: unattended`, invokes
  `python -m houmao.agents.launch_policy.cli` to resolve a versioned strategy
  for the detected CLI version before the final tool exec.
- if the manifest leaves operator prompt mode unset or `interactive`, execs the
  tool directly without unattended-policy synthesis.

Important launch-policy notes:

- unknown or unsupported CLI versions fail closed for unattended mode instead
  of guessing,
- `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` exists for transient debugging only,
- current supported unattended strategy details live in
  [Realm Controller](realm_controller.md#versioned-unattended-launch-policy).

Once you want repo-owned lifecycle control instead of raw helper execution, the next references are:

- [Realm Controller](realm_controller.md)
- [Runtime-Managed Agents Reference](./agents/index.md)
- [Agent Gateway Reference](./gateway/index.md)

## Roles

Roles live under `roles/<role>/system-prompt.md`.

Today, roles are applied manually (copy/paste as the first prompt) unless the
tool provides a native system/developer prompt injection mechanism.

For repo-owned session lifecycle workflows (build/start/resume/stop, including
CAO-backed sessions), use the [Realm Controller](realm_controller.md)
module and CLI.

## Programmatic Use (Python)

```python
from pathlib import Path

from houmao.agents import BuildRequest, build_brain_home

result = build_brain_home(
    BuildRequest(
        agent_def_dir=Path("."),
        runtime_root=Path("/abs/path/houmao-runtime"),
        tool="codex",
        skills=["openspec-apply-change"],
        config_profile="default",
        credential_profile="personal-a-default",
    )
)

print(result.home_path)
print(result.manifest_path)
```
