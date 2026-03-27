# Shared Registry Discovery And Cleanup

This page explains the operator-facing behavior of the shared registry: when the runtime uses it for name-based discovery, how fallback interacts with tmux-local pointers, and what `cleanup-registry` actually removes.

## Mental Model

The runtime does not lead with the shared registry. It leads with tmux-local discovery and uses the registry as the recovery path when tmux-local pointers are missing or stale.

That gives the current tmux session environment first say when it is healthy, while still letting the runtime recover sessions that live under different runtime roots.

## Name-Based Discovery Order

For name-addressed tmux-backed control such as `send-prompt`, `send-keys`, `mail`, and `stop-session`, the current order is:

1. normalize the input to canonical `AGENTSYS-...` form,
2. try tmux-local discovery first,
3. fall back to the shared registry when tmux-local discovery is unavailable,
4. validate the resolved manifest and agent-definition pointers before resuming control.

Path-like manifest identities do not use the shared registry. They go straight to the addressed `manifest.json`.

## What Counts As Fallback-Eligible

The shared registry is used when tmux-local discovery cannot give the runtime a valid target.

Current fallback-eligible cases include:

- the tmux session does not exist,
- `AGENTSYS_MANIFEST_PATH` is missing or blank,
- `AGENTSYS_MANIFEST_PATH` points to a missing manifest,
- `AGENTSYS_AGENT_DEF_DIR` is missing or blank,
- `AGENTSYS_AGENT_DEF_DIR` points to a missing directory.

Hard mismatches still fail fast instead of silently falling back:

- a manifest whose persisted tmux session identity does not match the addressed agent,
- a non-tmux-backed manifest reached through name-based resolution,
- explicitly invalid absolute-path requirements after a fresh registry record is loaded.

## Discovery Fallback Walkthrough

```mermaid
sequenceDiagram
    participant Op as Operator
    participant CLI as Runtime CLI
    participant TM as tmux<br/>discovery
    participant RG as Shared<br/>registry
    participant MF as manifest.json
    Op->>CLI: send-prompt<br/>--agent-identity gpu
    CLI->>TM: resolve manifest +<br/>agent_def_dir
    alt tmux pointers valid
        TM-->>CLI: resolved pointers
    else tmux missing or stale
        CLI->>RG: load fresh record<br/>for AGENTSYS-gpu
        alt fresh record found
            RG-->>CLI: manifest_path +<br/>agent_def_dir
        else no fresh record
            RG-->>CLI: stale or missing
        end
    end
    CLI->>MF: validate backend +<br/>tmux session identity
    MF-->>CLI: resolved target or error
```

The key idea is that registry fallback still ends with manifest validation. The registry helps the runtime find the candidate session; it does not skip the final integrity checks.

## Operator Examples

Use canonical or unprefixed names interchangeably:

```bash
pixi run python -m houmao.agents.realm_controller send-prompt \
  --agent-identity gpu \
  --prompt "Summarize the current plan"

pixi run python -m houmao.agents.realm_controller stop-session \
  --agent-identity AGENTSYS-gpu
```

Use an explicit registry root for isolated environments:

```bash
AGENTSYS_GLOBAL_REGISTRY_DIR=/abs/path/tmp/registry \
pixi run python -m houmao.agents.realm_controller send-prompt \
  --agent-identity gpu \
  --prompt "hello"
```

## Cleanup Semantics

`cleanup-registry` is the operator-facing janitor for stale `live_agents/` directories.

Default behavior:

- scan the effective `live_agents/` directory,
- remove directories whose `record.json` is missing,
- remove directories whose `record.json` is malformed,
- remove directories whose record lease expired longer ago than the grace period,
- preserve fresh directories,
- continue past per-directory removal failures and report them separately.

Examples:

```bash
pixi run houmao-mgr admin cleanup-registry
pixi run houmao-mgr admin cleanup-registry --grace-seconds 0
```

Representative result:

```json
{
  "failed_agent_ids": ["<stale-agent-id-that-could-not-be-removed>"],
  "failed_count": 1,
  "grace_seconds": 0,
  "preserved_agent_ids": ["<fresh-agent-id>"],
  "preserved_count": 1,
  "registry_root": "/abs/path/registry",
  "removed_agent_ids": ["<expired-agent-id>", "malformed"],
  "removed_count": 2
}
```

Interpret the buckets like this:

- `removed_agent_ids`: stale state that was successfully deleted,
- `preserved_agent_ids`: directories that still represent fresh live records,
- `failed_agent_ids`: stale directories that cleanup wanted to delete but could not remove.

## Cleanup Walkthrough

```mermaid
sequenceDiagram
    participant Op as Operator
    participant CLI as Runtime CLI
    participant RG as live_agents/
    Op->>CLI: cleanup-registry<br/>--grace-seconds 0
    CLI->>RG: scan candidate dirs
    loop each directory
        CLI->>RG: read record.json
        alt missing, malformed, or expired
            CLI->>RG: remove directory
        else fresh
            RG-->>CLI: preserve directory
        end
    end
    CLI-->>Op: removed + preserved + failed summary
```

## Current Implementation Notes

- `cleanup-registry` does not make currently live records go away just because the directory exists; lease freshness remains the deciding signal.
- A malformed record is treated as stale for lookup and as removable for cleanup.
- The cleanup command uses the same effective root-resolution logic as publication and lookup, so `AGENTSYS_GLOBAL_REGISTRY_DIR` changes all three paths together.

## Source References

- [`src/houmao/agents/realm_controller/cli.py`](../../../../src/houmao/agents/realm_controller/cli.py)
- [`src/houmao/agents/realm_controller/registry_storage.py`](../../../../src/houmao/agents/realm_controller/registry_storage.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../../src/houmao/agents/realm_controller/runtime.py)
- [`tests/unit/agents/realm_controller/test_registry_storage.py`](../../../../tests/unit/agents/realm_controller/test_registry_storage.py)
- [`tests/unit/agents/realm_controller/test_runtime_agent_identity.py`](../../../../tests/unit/agents/realm_controller/test_runtime_agent_identity.py)
