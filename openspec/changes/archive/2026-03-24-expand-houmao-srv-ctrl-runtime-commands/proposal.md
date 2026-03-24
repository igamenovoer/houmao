## Why

`houmao-srv-ctrl` already owns the supported `houmao-server + houmao-srv-ctrl` pair boundary, but its native top-level command surface is still too narrow to act as the main pair operations CLI. Operators still need to switch to `houmao-cli` for many runtime-oriented actions, which splits pair-native workflows across two binaries even when the underlying authority is already `houmao-server`, runtime-owned manifests, or the live gateway surface.

This is a good time to expand `houmao-srv-ctrl` because the current command-boundary design already reserves its top-level namespace for Houmao-owned semantics, and `houmao-server` already exposes most managed-agent read and control routes needed for a richer native command tree. The goal is to let `houmao-srv-ctrl` grow into the preferred pair-native CLI without retiring `houmao-cli` yet.

## What Changes

- Add a Houmao-owned native command tree on `houmao-srv-ctrl` centered on `agents`, `brains`, and `admin`.
- Define `houmao-srv-ctrl agents ...` as the preferred pair-native surface for managed-agent discovery, state and history inspection, prompt and interrupt submission, stop flows, gateway lifecycle, and mail-oriented follow-up actions.
- Retire the legacy top-level `houmao-srv-ctrl agent-gateway ...` surface and move gateway attach flows and future gateway operations under `houmao-srv-ctrl agents gateway ...`.
- Keep top-level `launch` and `install` as pair convenience commands and keep `houmao-srv-ctrl cao ...` as the explicit CAO compatibility namespace.
- Keep `houmao-cli` unchanged for compatibility while allowing `houmao-srv-ctrl` to absorb overlapping workflows and become the documented pair-native operator surface over time.
- Update repo-owned docs under `docs/` to replace `houmao-cli` usage with `houmao-srv-ctrl` whenever the new native pair CLI covers the workflow, while keeping `houmao-cli` documentation only where the workflow is not yet covered.
- Document the managed-agent history retention model in `docs/`, including what stays in memory versus what is persisted on disk, so operators can reason about long-running task footprint and cleanup expectations.
- Extend `houmao-server` only where needed to make the `agents` tree authoritative and transport-neutral, especially for stop semantics and server-mediated gateway and mail control.
- Keep build-time and host-local maintenance actions in `houmao-srv-ctrl` as local commands rather than forcing them through `houmao-server`.

## Capabilities

### New Capabilities
- `houmao-srv-ctrl-native-cli`: Houmao-owned native command families on `houmao-srv-ctrl` for pair-native agent control, local brain build, and local maintenance.

### Modified Capabilities
- `houmao-server-agent-api`: expand the managed-agent API where current routes are insufficient for the new `houmao-srv-ctrl agents ...` contract.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/*`, `src/houmao/server/app.py`, `src/houmao/server/service.py`, `src/houmao/server/client.py`, `src/houmao/server/models.py`
- Affected docs: repo-owned docs under `docs/`, especially pair CLI reference, gateway operations docs, history and retention guidance, and migration guidance, which should replace `houmao-cli` examples with `houmao-srv-ctrl` wherever the new native surface applies while keeping `houmao-cli` only for uncovered workflows and explicitly documenting what managed-agent history accumulates in memory versus on disk
- Affected tests: CLI routing, managed-agent command behavior, gateway and mail flows, and repo-owned command examples that currently reference `agent-gateway`
