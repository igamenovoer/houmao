# Plain Agent Definition Fixture Root

This fixture lane is the maintained secret-free direct-dir tree for explicit `--agent-def-dir` workflows. It models the plain filesystem contract only; it is not a project-overlay substitute, and it does not own host-local credentials.

```text
tests/fixtures/plain-agent-def/
  skills/<skill>/SKILL.md
  roles/<role>/system-prompt.md
  presets/<preset>.yaml
  launch-profiles/<name>.yaml
  tools/<tool>/adapter.yaml
  tools/<tool>/setups/<setup>/...
  tools/<tool>/auth/
  compatibility-profiles/   # optional compatibility metadata retained for specialized flows
```

## Use This Lane When

- a direct-dir test or helper needs one tracked secret-free source tree
- a workflow wants to copy a plain agent-definition root into a temp workdir
- a manual smoke flow needs to materialize auth into a copied direct-dir root

## Do Not Use This Lane When

- you need host-local credentials directly; use `tests/fixtures/auth-bundles/`
- you need a maintained project-aware source tree; use a fresh `.houmao/` overlay
- you need one maintained demo-local source tree; use that demo's tracked `inputs/agents/`

## Auth Contract

`tools/<tool>/auth/` exists here only as the plain direct-dir mount point. The tracked tree stays secret-free.

When a direct-dir workflow needs local credentials, materialize them into a copied temp root under `tools/<tool>/auth/<name>/`, or create a run-local alias from `tests/fixtures/auth-bundles/<tool>/<bundle>/`.

## Recommended Workflow

1. Select a tracked preset such as `tests/fixtures/plain-agent-def/presets/gpu-kernel-coder-claude-default.yaml`.
2. Build explicitly from this root:
   - `pixi run houmao-mgr brains build --agent-def-dir tests/fixtures/plain-agent-def --preset tests/fixtures/plain-agent-def/presets/gpu-kernel-coder-claude-default.yaml`
3. If the run needs host-local auth, copy or link the chosen bundle from `tests/fixtures/auth-bundles/` into a temp direct-dir root instead of mutating the tracked tree.
