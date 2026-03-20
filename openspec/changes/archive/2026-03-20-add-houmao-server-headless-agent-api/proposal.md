## Why

`houmao-server` is currently terminal-centric. Its Houmao-owned routes and live tracking assume CAO/TUI sessions identified by `terminal_id`, which makes Claude headless sessions awkward to expose even though the runtime already gives them a clearer contract: a persisted manifest, a stable resume `session_id`, and structured per-turn artifacts such as `stdout.jsonl`, `stderr.log`, and exit status.

We need a first-class server API for those headless agents so callers can launch them, discover them, inspect coarse state, and submit prompt turns through HTTP without pretending they are raw terminals or delegated CAO sessions. That API also needs an explicit server-owned authority model so restart recovery, single-active-turn gating, and interrupt routing do not depend on runtime in-memory state alone.

## What Changes

- Add a new Houmao-owned managed-agent API under `houmao-server` that introduces transport-neutral `/houmao/agents/*` discovery, identity, state, and bounded history routes for both TUI-backed and headless agents.
- Add Houmao-native headless lifecycle routes under `houmao-server` for headless launch, stop, discrete prompt turns, turn status, structured turn events, headless artifacts, and interrupt requests.
- Keep existing CAO-compatible `/sessions/*` and `/terminals/*` routes unchanged and keep current `/houmao/terminals/{terminal_id}/*` routes as TUI-oriented compatibility surfaces rather than forcing headless agents into `terminal_id` semantics.
- Make headless agents a Houmao-native server-managed transport: launching, persistence, and turn execution need not go through CAO or child-CAO registration.
- Add a dedicated server-owned managed-agent authority store under the `houmao-server` state tree, keyed by tracked-agent id, with persisted headless launch records and active-turn records so restart reconciliation does not depend on runtime in-memory fields.
- Define the raw native headless launch route around resolved runtime inputs such as `tool`, `working_directory`, `agent_def_dir`, `brain_manifest_path`, and `role_name`, while keeping pair-style `--agents` / `--provider` convenience translation in `houmao-srv-ctrl`.
- Expose a smaller transport-neutral agent state model on the shared `/houmao/agents/*` routes, with shared identity and coarse turn posture fields that TUI trackers can map into and headless trackers can derive directly from manifest and artifact evidence.
- Clarify that shared `/houmao/agents/{agent_ref}/history` remains bounded coarse recent history across both transports, while durable headless detail lives under `/turns/{turn_id}`.
- Make `houmao-srv-ctrl launch --headless` an additive Houmao-owned path that targets `houmao-server` native headless launch instead of delegating to `cao launch`.
- Preserve additive-extension safety: new managed-agent routes remain Houmao-owned routes outside the CAO-compatible API, and existing compatibility routes do not gain mandatory Houmao-only arguments.

## Capabilities

### New Capabilities

- `houmao-server-agent-api`: A transport-neutral Houmao-owned HTTP API for managed-agent discovery and coarse state across TUI and headless agents, plus native headless launch and stop plus headless-specific prompt-turn and artifact-inspection routes.

### Modified Capabilities

- `houmao-server`: expand server-owned tracking and extension-route authority so `houmao-server` can launch and manage headless agents natively through a dedicated managed-agent authority store and persisted active-turn records, while preserving existing CAO-compatible routes and TUI compatibility routes.
- `houmao-srv-ctrl-cao-compat`: treat `launch --headless` as an additive Houmao-owned launch path that targets `houmao-server` directly and translates pair convenience inputs into the native resolved-runtime launch request instead of delegating that headless case through `cao`.

## Impact

- `houmao-server` HTTP models, routing, service logic, and native headless lifecycle flows under `src/houmao/server/`
- Server-owned live tracking and registry code, including a dedicated `state/managed_agents/<tracked-agent-id>/` authority store, persisted active-turn records, new headless-aware identity handling, and shared state projection paths
- Possible extraction or reuse of headless turn-artifact parsing helpers from runtime code so the server and runtime consume the same machine-readable headless evidence
- `houmao-srv-ctrl` launch-path changes for native headless launch routing and convenience-to-native request translation
- New tests for shared `/houmao/agents/*` routes, native headless launch plus turn submission/status/event inspection, restart recovery from persisted authority and active-turn records, and coexistence with current TUI terminal routes
- Reference and developer docs for `houmao-server` and the paired `houmao-server + houmao-srv-ctrl` workflow, including the split between CAO-backed TUI launch and Houmao-native headless launch and the bounded-coarse meaning of shared `/history`
