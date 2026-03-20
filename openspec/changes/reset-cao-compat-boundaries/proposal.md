## Why

The current `houmao-server + houmao-srv-ctrl` pair still presents CAO compatibility as the default outer shape: CAO-compatible HTTP routes live at the server root, and CAO verbs still occupy the top level of `houmao-srv-ctrl`. That makes the public boundary dishonest. Houmao-native behavior already exists, but it looks secondary because CAO compatibility still owns the root namespaces.

We need to reset that contract now because the supported story is the Houmao pair, not mixed operation with raw upstream `cao` or `cao-server`. Keeping CAO at the root keeps leaking compatibility constraints into server routing, CLI shape, runtime clients, and gateway code even though the pair is explicitly allowed to diverge.

## What Changes

- **BREAKING** Move the CAO-compatible HTTP surface from root routes into an explicit `/cao/*` namespace on `houmao-server`.
- **BREAKING** Remove root-level CAO-compatible HTTP routes such as `/sessions/*` and `/terminals/*` from `houmao-server` instead of keeping them as public aliases.
- Keep Houmao-native HTTP routes under `/houmao/*`, and treat root-level server routes such as `/health` as Houmao-owned pair routes rather than CAO-compatible routes.
- **BREAKING** Remove top-level CAO verbs from `houmao-srv-ctrl`; expose CAO compatibility only through `houmao-srv-ctrl cao ...`.
- Redefine top-level `houmao-srv-ctrl` commands as Houmao-owned pair commands, with `launch` and `install` remaining top-level pair UX and raw CAO-oriented behavior moved under the `cao` namespace.
- Repair internal pair breakage by keeping persisted `api_base_url` values rooted at the public `houmao-server` authority and routing `/cao/*` through one shared pair-owned compatibility client seam used by server clients, runtime backends, gateway code, demos, tests, and docs.
- Replace root-level parity checks with namespaced parity checks so CAO compatibility is verified against `/cao/*` and `houmao-srv-ctrl cao ...`, not against the top-level server and CLI shapes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-server`: change the public compatibility contract so CAO-compatible HTTP routes live only under `/cao/*`, while root and `/houmao/*` remain Houmao-owned server surfaces.
- `houmao-srv-ctrl-cao-compat`: change the CLI contract so CAO compatibility lives only under `houmao-srv-ctrl cao ...`, while top-level `houmao-srv-ctrl` subcommands become Houmao-owned pair commands rather than CAO-shaped passthrough verbs.

## Impact

- `src/houmao/server/app.py`, `src/houmao/server/client.py`, and server query/CLI helpers that currently assume CAO routes live at the server root
- `src/houmao/srv_ctrl/commands/*` and the public `houmao-srv-ctrl` command tree
- Pair-owned runtime and gateway integration that currently routes `houmao_server_rest` control through root CAO paths, including persisted manifest and attach flows rooted in `api_base_url`, such as `src/houmao/agents/realm_controller/backends/houmao_server_rest.py` and `src/houmao/agents/realm_controller/gateway_service.py`
- Repo-owned demos and demo-backed tests that instantiate `HoumaoServerClient` and currently inherit root-shaped CAO session or terminal paths
- Unit and integration coverage that currently asserts root-route or top-level-verb CAO parity, plus verification that needs to preserve script-facing `houmao-srv-ctrl cao ...` behavior
- Reference, migration, and developer docs for the `houmao-server + houmao-srv-ctrl` pair
