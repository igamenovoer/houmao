# Run Log: `project init` reports `agent_def_dir` as `.houmao/agents` before that directory exists

## Summary

During an interactive check of `houmao-mgr project init`, the command succeeded and returned an `agent_def_dir` pointing at `<project-root>/.houmao/agents`, and the generated config stored `[paths] agent_def_dir = "agents"`, but the initialized overlay did not actually contain a `.houmao/agents/` directory yet.

## Environment

- Date: 2026-03-29 UTC
- Repo: `/data1/huangzhe/code/houmao`
- Command: `pixi run houmao-mgr project init`
- Generated config: `/data1/huangzhe/code/houmao/.houmao/houmao-config.toml`

## Commands

```bash
pixi run houmao-mgr project init
sed -n '1,120p' .houmao/houmao-config.toml
find .houmao -maxdepth 3 -mindepth 1 | sort
```

## Observed Behavior

`project init` returned:

```text
"agent_def_dir": "/data1/huangzhe/code/houmao/.houmao/agents"
```

The generated config contained:

```toml
schema_version = 1

[paths]
agent_def_dir = "agents"
```

But the initialized overlay contents did not include `.houmao/agents/`; only catalog-backed overlay roots such as `.houmao/content/` were present immediately after init.

## Interpretation

The underlying design is lazy compatibility projection materialization: `.houmao/agents/` is the compatibility agent-definition root, but it is not created at `project init` time. That part is consistent with the docs and implementation.

The bug is operator-facing clarity:

- `project init` emits an `agent_def_dir` path that does not yet exist
- the config still points at `agents`, which reads like an initialized on-disk source root
- the immediate post-init filesystem layout does not match that expectation

This is likely to confuse operators into thinking init either failed to create the configured path or that the naming contract changed unexpectedly.

## Supporting References

- `src/houmao/project/overlay.py`
  - `render_default_project_config()` writes `agent_def_dir = "agents"`
  - `bootstrap_project_overlay()` does not create `.houmao/agents/`
- `docs/reference/cli.md`
  - explicitly states that Houmao materializes `.houmao/agents/` as a compatibility projection when a file-tree consumer needs it

## Suggested Fix

Choose one of these and document it consistently:

1. Keep lazy materialization, but change `project init` output and config-facing docs to say this is a compatibility projection path that may not exist until materialized.
2. Materialize `.houmao/agents/` during `project init` so the reported/generated path exists immediately.

The smaller fix is probably option 1.
