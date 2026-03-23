## 1. Public API Contract

- [x] 1.1 Add Pydantic models for the shared `/houmao/agents/*` read surface and for native headless launch, stop, and turn request and response payloads around the resolved launch fields `tool`, `working_directory`, `agent_def_dir`, `brain_manifest_path`, and `role_name`.
- [x] 1.2 Add FastAPI routes and client helpers for `GET /houmao/agents`, `GET /houmao/agents/{agent_ref}`, `GET /houmao/agents/{agent_ref}/state`, and `GET /houmao/agents/{agent_ref}/history`, with `/history` explicitly modeled as bounded coarse recent history rather than a durable per-turn log.
- [x] 1.3 Add FastAPI routes and client helpers for native headless `launches`, `stop`, `turns`, `events`, `artifacts`, and `interrupt` endpoints, including explicit `422` validation for missing or convenience-only launch inputs, while keeping existing `/sessions/*`, `/terminals/*`, and `/houmao/terminals/{terminal_id}/*` routes unchanged.

## 2. Authority And Managed-Agent Registry

- [x] 2.1 Keep the existing TUI registration bridge intact while adding a separate native headless authority store under `state/managed_agents/<tracked_agent_id>/authority.json` for launch authority, manifest paths, session roots, and stable headless identity metadata.
- [x] 2.2 Add persisted `active_turn.json` records under the same authority subtree and implement restart reconciliation so single-active-turn gating and interrupt targeting survive server restart.
- [x] 2.3 Introduce a server-owned managed-agent identity plus alias-resolution layer and registry rebuild path that use TUI registration for terminal-backed sessions and native headless authority records for server-launched headless agents without fabricating terminal ids.

## 3. Native Headless Lifecycle And State Projection

- [x] 3.1 Extract or reuse shared headless launch, stop, execution, and event-parsing helpers from the runtime so `houmao-server` can create and control manifest-bound headless agents without duplicating CLI contract logic.
- [x] 3.2 Implement native headless launch around the resolved runtime request model, return tracked-agent plus manifest/session-root pointers, and persist the matching server-owned authority records.
- [x] 3.3 Implement stop, turn submission, single-active-turn gating, best-effort interrupt, turn-status inspection, structured event projection, durable artifact serving, and shared state/history projection so per-turn durability stays under `/turns/{turn_id}` while shared `/history` remains bounded and coarse.

## 4. CLI Integration, Verification, And Documentation

- [x] 4.1 Update `houmao-srv-ctrl launch --headless` to translate pair convenience inputs such as `--agents` and `--provider` into the resolved native launch request and call the native server launch path instead of delegating that mode through `cao`, while keeping delegated `cao launch` for the TUI path.
- [x] 4.2 Add unit and integration coverage for native headless launch validation, authority-store creation, active-turn persistence and restart recovery, alias resolution, shared `/houmao/agents/*` responses, bounded `/history` semantics, headless turn conflict handling, artifact and event inspection, `houmao-srv-ctrl` headless launch translation, and coexistence with current terminal-keyed routes.
- [x] 4.3 Update `houmao-server` and `houmao-srv-ctrl` reference and developer docs to describe the shared managed-agent routes, the `state/managed_agents/<tracked_agent_id>/` authority model, native headless lifecycle routes, the split between TUI compatibility and native headless launch, the resolved native launch request model, and the new meaning of `launch --headless`.
