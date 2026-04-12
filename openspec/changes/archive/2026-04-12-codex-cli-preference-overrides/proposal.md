## Why

Codex merges configuration from `CODEX_HOME` and project-local `.codex/config.toml` discovered from the launch working directory, so Houmao-managed preferences written only to the generated Codex home can be overridden by an unrelated project config. This breaks the launch-owned model/reasoning and unattended-policy contract when a workspace already has Codex defaults such as `model_reasoning_effort = "high"`.

## What Changes

- Pass Houmao-resolved Codex preferences through final Codex CLI config override arguments so they win over project-local `.codex/config.toml` layers.
- Continue writing the same non-secret preferences into the generated Codex runtime `config.toml` as a durable fallback and inspection artifact for launches where no project-local `.codex/config.toml` interferes.
- Treat Codex CLI config overrides as the authoritative launch surface for Houmao-owned non-secret preferences such as model, reasoning effort, unattended approval/sandbox posture, selected model provider, and provider contract fields when Houmao owns the provider selection.
- Keep secret material out of CLI arguments; API keys and auth state remain env/file based.
- Preserve explicit manual passthrough semantics so an operator who invokes a generated `launch.sh` with additional trailing args can still intentionally override the generated defaults for that one manual launch.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `agent-model-selection`: Codex model and reasoning projection must include authoritative CLI config overrides in addition to the existing runtime-home config projection.
- `brain-launch-runtime`: Codex launch-plan and launch-helper assembly must place Houmao-owned non-secret preferences in final CLI config override args so they beat cwd/project Codex config layers while retaining generated home config as fallback state.
- `versioned-launch-policy-registry`: Codex unattended strategy ownership must include equivalent CLI config-override launch surfaces for strategy-owned preferences, not only runtime-home `config.toml` mutation.

## Impact

- Affected code includes Codex model projection, generated `launch.sh` synthesis, runtime launch-plan reconstruction, Codex headless per-turn execution overrides, and Codex unattended launch-policy strategy handling.
- Tests should cover local interactive/raw helper launch, runtime-managed Codex headless launch, per-turn headless execution overrides, and a regression where cwd project `.codex/config.toml` conflicts with the generated Codex home.
- No user-project files should be mutated to solve this; the fix belongs in Houmao launch arguments and generated runtime homes.
