## Why

Houmao already owns the public pair boundary, live TUI tracking, parsing, and managed-agent state, but it still depends on CAO for a narrow control slice: session and terminal lifecycle, CAO-shaped transport routes, provider bootstrap quirks, and profile-install behavior. That dependency keeps a heavy external framework in the critical path, constrains Houmao to CAO implementation behavior, and forces the pair to preserve a child-CAO shallow cut even though the supported product boundary is already `houmao-server + houmao-srv-ctrl`.

## What Changes

- **BREAKING** Replace the child-CAO shallow cut with a Houmao-owned native CAO-compatible control core that serves the current pair behavior directly.
- **BREAKING** Keep `houmao-server` and `houmao-srv-ctrl` working as the supported pair, including the existing `/cao/*` HTTP namespace and `houmao-srv-ctrl cao ...` CLI namespace, but implement those surfaces through Houmao-owned control components instead of a supervised `cao-server` child or installed `cao` delegation.
- Introduce an explicit Houmao-owned internal seam for the absorbed control slice: tmux lifecycle, terminal registry, provider adapters, profile store, compatibility payload projection, and pair-facing compatibility routing.
- Shape that seam so future upstream CAO ideas can be imported by capability at clear insertion points instead of by restoring CAO as a runtime dependency.
- **BREAKING** Retire raw CAO-facing runtime entrypoints outside the supported pair. If `houmao-cli` CAO-backed flows or other raw-CAO runtime paths are invoked after this change, they fail fast with an explicit migration error that points callers to `houmao-server` and `houmao-srv-ctrl`.
- **BREAKING** Retire `houmao-cao-server` and the standalone CAO launcher path. Invocations fail fast with migration guidance to the supported pair rather than trying to preserve child-CAO lifecycle behavior.
- Preserve the Houmao-owned root and `/houmao/*` server boundary and keep current pair-managed agent, gateway, mailbox, and tracking flows working on top of the new Houmao-owned control authority.

## Capabilities

### New Capabilities
- `houmao-cao-control-core`: define the Houmao-owned native CAO-compatible session and terminal control core that replaces child-CAO runtime dependency while preserving explicit pair compatibility surfaces.

### Modified Capabilities
- `houmao-server`: replace child-CAO shallow-cut authority with the Houmao-owned control core while preserving the supported `/cao/*`, root, and `/houmao/*` public server contract for the pair.
- `houmao-srv-ctrl-cao-compat`: replace installed-`cao` and child-CAO dependence in the supported pair CLI with pair-owned compatibility implementations over the Houmao control core.
- `cao-rest-client-contract`: redirect the repo-owned CAO-compatible client contract to the Houmao-owned compatibility authority and remove dependence on raw runtime CAO sessions as the supported path.
- `brain-launch-runtime`: retire raw CAO-backed runtime entrypoints outside the pair and require migration guidance toward `houmao-server` plus `houmao-srv-ctrl`.
- `cao-server-launcher`: retire the standalone CAO launcher and `houmao-cao-server` surface in favor of explicit migration failure behavior.

## Impact

- Affected code includes `src/houmao/server/*`, `src/houmao/srv_ctrl/*`, `src/houmao/cao/*`, `src/houmao/agents/realm_controller/backends/cao_rest.py`, `src/houmao/agents/realm_controller/backends/houmao_server_rest.py`, and pair-facing gateway or demo code that still assumes a child-CAO authority.
- Affected dependencies include removal of CAO runtime-process and CLI delegation from the supported pair path, while preserving tmux and provider-specific launch behavior inside Houmao-owned code.
- Affected CLIs and APIs include `/cao/*` compatibility routing, `houmao-srv-ctrl cao ...`, top-level pair launch and install, and retirement behavior for `houmao-cli` CAO-backed paths plus `houmao-cao-server`.
- Affected docs and tests include pair architecture docs, CAO compatibility docs, launcher docs, migration guidance, and regression coverage that currently assumes a child `cao-server` or installed `cao` remains part of the supported path.
