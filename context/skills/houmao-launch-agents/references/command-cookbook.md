# Houmao Launch Agents Cookbook

## Shared Defaults

- Run from the repository root.
- Use `--agent-def-dir tests/fixtures/agents`.
- Use `tmp/houmao-launch-agents/<run-id>/...` for generated artifacts.
- Builder output manifests currently land at `<runtime-root>/manifests/<home-id>.yaml`.
- Trust the builder output `manifest_path` field if a stale document shows another layout.

## Restore Local Fixture Credentials

Run this only if `tests/fixtures/agents/brains/api-creds/` is missing or incomplete:

```bash
set -a && . ./.env && set +a
gpg --batch --yes --pinentry-mode loopback \
  --passphrase "$AGENT_CREDENTIAL_COMPRESS_PASSWORD" \
  -d tests/fixtures/agents/brains/api-creds.tar.gz.gpg | tar -xzf - -C tests/fixtures/agents/brains
```

Do not commit anything under `tests/fixtures/agents/brains/api-creds/`.

## Prepare A Narrow Dummy-Project Workdir

Use this for bounded `minimal launch` or `full launch` tests that should run outside the repo worktree:

```bash
RUN_ID="skill-demo-codex-$(date -u +%Y%m%dT%H%M%SZ)"
RUN_ROOT="tmp/houmao-launch-agents/$RUN_ID"
WORKDIR="$RUN_ROOT/project"
mkdir -p "$RUN_ROOT"
cp -R tests/fixtures/dummy-projects/mailbox-demo-python "$WORKDIR"
git -C "$WORKDIR" init -q
```

Use the real repository root as the workdir for repository-scale tests.

## Minimal Launch: Build A Brain With The Lower-Level Builder

### From Explicit Inputs

Codex:

```bash
RUNTIME_ROOT="$RUN_ROOT/runtime"
HOME_ID="manual-codex"

pixi run python scripts/agents/build_brain_home.py \
  --agent-def-dir tests/fixtures/agents \
  --runtime-root "$RUNTIME_ROOT" \
  --tool codex \
  --skill skill-invocation-probe \
  --config-profile default \
  --cred-profile personal-a-default \
  --home-id "$HOME_ID"
```

Claude:

```bash
RUNTIME_ROOT="$RUN_ROOT/runtime"
HOME_ID="manual-claude"

pixi run python scripts/agents/build_brain_home.py \
  --agent-def-dir tests/fixtures/agents \
  --runtime-root "$RUNTIME_ROOT" \
  --tool claude \
  --skill openspec-explore \
  --config-profile default \
  --cred-profile personal-a-default \
  --home-id "$HOME_ID"
```

### From A Recipe

This still stays in `minimal launch` as long as you use a brain recipe only and do not use a blueprint or role:

```bash
pixi run python scripts/agents/build_brain_home.py \
  --agent-def-dir tests/fixtures/agents \
  --runtime-root "$RUNTIME_ROOT" \
  --recipe brains/brain-recipes/codex/skill-invocation-demo-default.yaml \
  --home-id "$HOME_ID"
```

### From Python

```python
from pathlib import Path

from houmao.agents import BuildRequest, build_brain_home

result = build_brain_home(
    BuildRequest(
        agent_def_dir=Path("tests/fixtures/agents"),
        runtime_root=Path("tmp/houmao-launch-agents/python-build"),
        tool="codex",
        skills=["skill-invocation-probe"],
        config_profile="default",
        credential_profile="personal-a-default",
        home_id="python-manual-codex",
    )
)

print(result.home_path)
print(result.manifest_path)
print(result.launch_helper)
```

## Minimal Launch: Launch The Tool Manually

### Preferred Manual Launch: Generated Helper

Codex:

```bash
cd "$WORKDIR"
"$RUNTIME_ROOT/homes/$HOME_ID/launch.sh"
```

Claude:

```bash
cd "$WORKDIR"
"$RUNTIME_ROOT/homes/$HOME_ID/launch.sh"
```

The helper is still a `minimal launch` path. It does not create a Houmao-managed session. It only selects the generated home, runs the shared bootstrap, and then `exec`s the real `codex` or `claude` binary.

### Direct `codex` Or `claude` Launch Without `launch.sh`

Use this only if you intentionally need to bypass the generated helper and are willing to run bootstrap yourself.

Codex:

```bash
export CODEX_HOME="$RUNTIME_ROOT/homes/$HOME_ID"
cd "$WORKDIR"
pixi run python - <<'PY'
from pathlib import Path
import os

from houmao.agents.realm_controller.backends.codex_bootstrap import ensure_codex_home_bootstrap

ensure_codex_home_bootstrap(
    home_path=Path(os.environ["CODEX_HOME"]),
    env=dict(os.environ),
    working_directory=Path.cwd(),
)
PY
codex
```

Claude:

```bash
export CLAUDE_CONFIG_DIR="$RUNTIME_ROOT/homes/$HOME_ID"
cd "$WORKDIR"
pixi run python - <<'PY'
from pathlib import Path
import os

from houmao.agents.realm_controller.backends.claude_bootstrap import ensure_claude_home_bootstrap

ensure_claude_home_bootstrap(
    home_path=Path(os.environ["CLAUDE_CONFIG_DIR"]),
    env=dict(os.environ),
)
PY
claude -p
```

## Full Launch: Houmao Pipeline

### Blueprint Selection

| Use case | Codex blueprint | Claude blueprint |
| --- | --- | --- |
| Installed-skill trigger probe in a copied dummy project | `blueprints/skill-invocation-demo-codex.yaml` | `blueprints/skill-invocation-demo-claude.yaml` |
| Narrow mailbox or runtime-contract flow | `blueprints/mailbox-demo-codex.yaml` | `blueprints/mailbox-demo-claude.yaml` |
| Projection or parsing experiment in a small copied project | `blueprints/projection-demo-codex.yaml` | `blueprints/projection-demo-claude.yaml` |
| Repository-scale engineering behavior | `blueprints/gpu-kernel-coder-codex.yaml` or `blueprints/gpu-kernel-coder.yaml` | `blueprints/gpu-kernel-coder-claude.yaml` |

### Build + Launch A Managed Codex Session

```bash
RUNTIME_ROOT="$RUN_ROOT/runtime"
HOME_ID="managed-codex"
AGENT_NAME="AGENTSYS-skill-demo-codex"

pixi run python -m houmao.agents.realm_controller build-brain \
  --agent-def-dir tests/fixtures/agents \
  --runtime-root "$RUNTIME_ROOT" \
  --home-id "$HOME_ID" \
  --blueprint blueprints/skill-invocation-demo-codex.yaml

pixi run python -m houmao.agents.realm_controller start-session \
  --agent-def-dir tests/fixtures/agents \
  --runtime-root "$RUNTIME_ROOT" \
  --brain-manifest "$RUNTIME_ROOT/manifests/$HOME_ID.yaml" \
  --blueprint blueprints/skill-invocation-demo-codex.yaml \
  --backend codex_headless \
  --workdir "$WORKDIR" \
  --agent-identity "$AGENT_NAME"

pixi run python -m houmao.agents.realm_controller send-prompt \
  --agent-def-dir tests/fixtures/agents \
  --agent-identity "$AGENT_NAME" \
  --prompt "Write a one-line status note about the current repository."

pixi run python -m houmao.agents.realm_controller stop-session \
  --agent-def-dir tests/fixtures/agents \
  --agent-identity "$AGENT_NAME"
```

### Build + Launch A Managed Claude Session

```bash
RUNTIME_ROOT="$RUN_ROOT/runtime"
HOME_ID="managed-claude"
AGENT_NAME="AGENTSYS-skill-demo-claude"

pixi run python -m houmao.agents.realm_controller build-brain \
  --agent-def-dir tests/fixtures/agents \
  --runtime-root "$RUNTIME_ROOT" \
  --home-id "$HOME_ID" \
  --blueprint blueprints/skill-invocation-demo-claude.yaml

pixi run python -m houmao.agents.realm_controller start-session \
  --agent-def-dir tests/fixtures/agents \
  --runtime-root "$RUNTIME_ROOT" \
  --brain-manifest "$RUNTIME_ROOT/manifests/$HOME_ID.yaml" \
  --blueprint blueprints/skill-invocation-demo-claude.yaml \
  --backend claude_headless \
  --workdir "$WORKDIR" \
  --agent-identity "$AGENT_NAME"

pixi run python -m houmao.agents.realm_controller send-prompt \
  --agent-def-dir tests/fixtures/agents \
  --agent-identity "$AGENT_NAME" \
  --prompt "Write a one-line status note about the current repository."

pixi run python -m houmao.agents.realm_controller stop-session \
  --agent-def-dir tests/fixtures/agents \
  --agent-identity "$AGENT_NAME"
```

### Switch The Same Managed Lane To CAO

Use this only when the point of the test is CAO integration, shadow parsing, or gateway behavior:

```bash
pixi run python -m houmao.agents.realm_controller start-session \
  --agent-def-dir tests/fixtures/agents \
  --runtime-root "$RUNTIME_ROOT" \
  --brain-manifest "$RUNTIME_ROOT/manifests/$HOME_ID.yaml" \
  --blueprint blueprints/skill-invocation-demo-codex.yaml \
  --backend cao_rest \
  --cao-parsing-mode shadow_only \
  --workdir "$WORKDIR" \
  --agent-identity "$AGENT_NAME"
```

### Existing Managed Demo Packs

- `scripts/demo/skill-invocation-demo-pack/run_demo.sh --tool codex|claude`
- `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh`

## Maintained References

- `docs/reference/agents_brains.md`
- `docs/reference/realm_controller.md`
- `tests/fixtures/agents/README.md`
- `tests/fixtures/agents/brains/README.md`
- `scripts/demo/skill-invocation-demo-pack/README.md`
