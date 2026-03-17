# Issue: Default CAO Launcher Config Hardcodes A Non-Portable `home_dir`

## Status
Resolved on 2026-03-17.

## Resolution Summary
The checked-in launcher config now leaves `home_dir` empty, which lets the launcher use its portable built-in home-directory resolution instead of requiring a machine-specific absolute path.

## Summary

The checked-in launcher config at `config/cao-server-launcher/local.toml` currently hardcodes:

```toml
home_dir = "/data/agents/cao-home"
```

That path is not portable across developer environments. In environments where `/data/agents/` does not exist or is not writable, the default launcher command fails before `cao-server` can start.

This should be treated as a system-level issue rather than a tutorial-pack-only problem, because any workflow that relies on the repo's default launcher config inherits the same fragility.

## What Failed

Observed during mailbox tutorial-pack testing on 2026-03-16:

```bash
pixi run python -m houmao.cao.tools.cao_server_launcher start --config config/cao-server-launcher/local.toml
```

Result:

```text
PermissionError: [Errno 13] Permission denied: '/data/agents'
```

## Current Behavior

- `config/cao-server-launcher/local.toml` pins `home_dir` to `/data/agents/cao-home`.
- Launcher config parsing requires `home_dir` to be a non-empty absolute path when present.
- Launcher runtime code already has a built-in fallback when `home_dir` is absent: `_resolve_home_dir()` uses `runtime_root/cao_servers/<host>-<port>/home`.
- But the checked-in local config does not use that fallback because it always supplies the hardcoded absolute path.

Relevant files:

- [local.toml](/data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents/config/cao-server-launcher/local.toml)
- [server_launcher.py](/data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents/src/houmao/cao/server_launcher.py)

## Why This Matters

- The repository's default CAO launcher path is not safe to assume across machines.
- Tutorials and demos can fail on launcher startup for filesystem-permission reasons that are unrelated to the actual feature under test.
- Developers end up working around the issue with ad hoc `--home-dir` overrides instead of relying on the checked-in default config.

## Desired Direction

The default `home_dir` in repo-owned launcher config should be allowed to be empty to mean system-defined home dir.

In practice, that means the checked-in default config should not require a host-specific absolute launcher home path. A developer running from the repo root should be able to use the default launcher config without first editing a machine-local path under `/data/...`.

If the implementation wants to preserve the current fallback behavior, then "system-defined home dir" can map to the launcher's built-in effective home selection rather than a repo-hardcoded path. The important part is that the default checked-in config should remain portable.

## Suggested Follow-Up

- Decide whether launcher config should treat missing or empty `home_dir` as "use system-defined launcher home".
- Update `config/cao-server-launcher/local.toml` so the checked-in default no longer depends on `/data/agents/cao-home`.
- Add coverage for launcher startup using the default checked-in config in an environment without `/data/agents/`.
