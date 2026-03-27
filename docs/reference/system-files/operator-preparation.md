# Operator Preparation

This page turns the filesystem reference into preparation guidance: what you can pre-create, what must be writable, what can be redirected, and which directories are durable versus scratch.

## Before First Run

The safest preparation pattern is:

1. choose where durable runtime and registry state should live,
2. choose whether workspace-local jobs should stay in the repo worktree or move to a scratch filesystem,
3. choose whether the legacy launcher-managed CAO state should use an explicit `home_dir` (only relevant for `cao_rest` backend),
4. pre-create any redirected parent directories with the right ownership and write permissions.

## Writable-Path Summary

| Path family | May pre-create parent directories? | Must be writable? | Durable or scratch? | Notes |
| --- | --- | --- | --- | --- |
| Runtime root and parents | yes | yes | Durable | Needed for generated homes, manifests, sessions, and launcher trees |
| Registry root and parents | yes | yes | Durable | Needed for `live_agents/<agent-id>/record.json` publication and cleanup |
| Workspace-local jobs root | yes | yes | Scratch | Best candidate for fast local scratch or redirected temp storage |
| Explicit CAO `home_dir` | yes | yes | Tool-owned durable state | CAO writes under `HOME/.aws/cli-agent-orchestrator/` |
| Derived launcher `home/` | no pre-create required, but allowed via parent | yes | Tool-owned durable state | Derived automatically when launcher config omits `home_dir` |

Mailbox has its own preparation rules under [Mailbox Reference](../mailbox/index.md) and is not repeated here.

## Redirection Surfaces

Current high-value redirection surfaces:

| Surface | Current operator-facing override |
| --- | --- |
| Runtime root | `AGENTSYS_GLOBAL_RUNTIME_DIR`, entrypoint-specific explicit `runtime_root` override |
| Registry root | `AGENTSYS_GLOBAL_REGISTRY_DIR` |
| Local jobs root | `AGENTSYS_LOCAL_JOBS_DIR` |
| CAO launcher runtime root | launcher config or CLI `runtime_root` override |
| CAO `HOME` | launcher config or CLI `home_dir` override |

Representative redirection setup:

```bash
export AGENTSYS_GLOBAL_RUNTIME_DIR=/data/$USER/houmao-runtime
export AGENTSYS_GLOBAL_REGISTRY_DIR=/data/$USER/houmao-registry
export AGENTSYS_LOCAL_JOBS_DIR=/scratch/$USER/houmao-jobs
```

Representative launcher config:

```toml
base_url = "http://localhost:9889"
runtime_root = "/data/agents/houmao-runtime"
home_dir = "/data/agents/cao-home"
proxy_policy = "clear"
startup_timeout_seconds = 15
```

Important rule: env-var root overrides must be absolute paths. Explicit CLI or config overrides may resolve relative to the caller-specific base, but absolute paths remain the clearest operator-facing choice.

## Ignore Rules

The best default ignore rule target is the workspace-local jobs root:

```text
.houmao/jobs/
```

If you intentionally redirect the runtime root or registry root into a repo-local path, ignore those relocated directories too, but only when that matches your local operator workflow. Their contents are more durable than the jobs root and often worth inspecting before blanket cleanup.

## Cleanup Expectations

| Path family | Safe cleanup stance |
| --- | --- |
| `<working-directory>/.houmao/jobs/<session-id>/` | Usually safe to treat as scratch after the session is finished; `houmao-mgr agents cleanup session --include-job-dir` or `houmao-mgr admin cleanup runtime sessions --include-job-dir` can remove it together with a stopped session envelope |
| `<runtime-root>/sessions/<backend>/<session-id>/gateway/run/` and launcher/gateway log files | Ephemeral or log-style cleanup after verified stop is usually fine; use `houmao-mgr agents cleanup logs` or `houmao-mgr admin cleanup runtime logs` and do not treat stable gateway files such as `queue.sqlite`, `state.json`, or `events.jsonl` as log scratch |
| `<runtime-root>/homes/<home-id>/` and `<runtime-root>/manifests/<home-id>.yaml` | Safe to delete and rebuild when no live session still depends on them; `houmao-mgr admin cleanup runtime builds` enforces that preserved session manifests keep their referenced manifest-home pairs |
| `<runtime-root>/mailbox-credentials/stalwart/<credential-ref>.json` | Treat as durable secret material until no preserved session manifest still references that `credential_ref`; `houmao-mgr admin cleanup runtime mailbox-credentials` handles that classification |
| `<runtime-root>/sessions/<backend>/<session-id>/manifest.json` and stable gateway artifacts | Treat as durable runtime state while the session is active or resumable; `houmao-mgr agents cleanup session` and `houmao-mgr admin cleanup runtime sessions` remove whole stopped envelopes, while log cleanup intentionally leaves durable gateway state behind |
| `<runtime-root>/sessions/<backend>/<session-id>/mailbox-secrets/` | Session-local Stalwart secret material is cleanup-sensitive, not scratch; remove it only after the session is stopped, typically through `houmao-mgr agents cleanup mailbox` |
| `<registry-root>/live_agents/<agent-id>/record.json` | Let the runtime or `houmao-mgr admin cleanup registry` manage freshness; registry cleanup probes tmux-backed records locally by default, so do not treat fresh live entries as scratch |
| legacy `<registry-root>/live_agents/<agent-key>/` leftovers | Manual cleanup is acceptable after confirming they are pre-cutover leftovers |
| launcher-selected or explicit CAO home contents | Do not treat as Houmao scratch; CAO owns that state |

## Recommended Preparation Patterns

- Put durable runtime and registry roots on stable storage with normal user write access.
- Put workspace-local jobs on fast scratch storage when you want transient tool output away from the durable runtime root.
- Keep CAO `home_dir` on writable storage even if repos or worktrees are read-only.
- Prefer explicit absolute overrides in CI or multi-disk setups so operators can see the chosen storage contract directly in config or environment.

## Related References

- [Roots And Ownership](roots-and-ownership.md): Root precedence and ownership categories.
- [Agents And Runtime](agents-and-runtime.md): Which runtime artifacts are durable versus scratch-adjacent.
- [Legacy CAO Server](cao-server.md): Launcher and CAO-home placement details (legacy `cao_rest` backend only).
- [Shared Registry](shared-registry.md): Registry-root layout and cleanup boundary.

## Source References

- [`src/houmao/owned_paths.py`](../../../src/houmao/owned_paths.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../src/houmao/agents/realm_controller/runtime.py)
- [`src/houmao/agents/realm_controller/registry_storage.py`](../../../src/houmao/agents/realm_controller/registry_storage.py)
- [`src/houmao/cao/server_launcher.py`](../../../src/houmao/cao/server_launcher.py)
