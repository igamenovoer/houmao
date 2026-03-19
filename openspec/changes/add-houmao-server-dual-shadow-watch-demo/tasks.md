## 1. Extend Server-Owned Lifecycle Tracking For Demo Parity

- [ ] 1.1 Add server-owned lifecycle timing and stalled-state fields to the tracked-state models, config, client helpers, and query surfaces used by `houmao-server`.
- [ ] 1.2 Update the server tracking reducer and related tests so readiness/completion timing, `candidate_complete`, and `unknown -> stalled` are computed authoritatively in `houmao-server`.

## 2. Expose The Canonical Runner Surface With Fail-Fast Preflight

- [ ] 2.1 Create the new demo pack under `scripts/demo/houmao-server-dual-shadow-watch/` and the supporting package modules under `src/houmao/demo/houmao_server_dual_shadow_watch/`, including persisted run-state scaffolding.
- [ ] 2.2 Implement fail-fast preflight checks for required binaries, profile/config readiness, and port availability before any live launch begins.
- [ ] 2.3 Implement bounded server-start, delegated-launch, inspect, and stop behavior so the canonical runner exits explicitly on timeout instead of hanging.

## 3. Build The Demo Lifecycle And Server-Backed Monitoring

- [ ] 3.1 Implement demo startup to provision isolated projection-demo workdirs, start a demo-owned `houmao-server`, and launch Claude and Codex through `houmao-srv-ctrl launch` from the corresponding workdirs.
- [ ] 3.2 Implement persisted demo state plus `inspect` and `stop` flows that treat `houmao-server` as the session authority and preserve deterministic run artifacts and logs.
- [ ] 3.3 Implement the Rich monitor so it consumes `houmao-server` terminal state/history only and writes sample/transition NDJSON from the server-owned payloads it displays.

## 4. Add The Implemented HTT Surfaces

- [ ] 4.1 Add the demo-owned `autotest/` layout with a standalone harness, shared helpers, and an automatic preflight/start/inspect/stop case.
- [ ] 4.2 Add the interactive autotest guide for live shadow-state validation as an independent step-by-step procedure rather than a wrapper around the automatic case.
- [ ] 4.3 Ensure the implemented autotest cases and harness preserve stable output locations and machine-detectable pass/fail outcomes.

## 5. Verify And Document The Interactive Testing Workflow

- [ ] 5.1 Add tests covering the new demo driver/monitor behavior, lifecycle timing fields, and fail-fast/timeout behavior.
- [ ] 5.2 Write the new demo README and any supporting docs so operators understand the supported `houmao-server + houmao-srv-ctrl` boundary, prerequisites, canonical interactive workflow, and autotest surfaces.
