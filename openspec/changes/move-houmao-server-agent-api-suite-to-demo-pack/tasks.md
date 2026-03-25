## 1. Define the HTT Case Contract First

- [x] 1.1 Add and review `openspec/changes/move-houmao-server-agent-api-suite-to-demo-pack/testplans/case-real-agent-preflight.md`.
- [x] 1.2 Add and review `openspec/changes/move-houmao-server-agent-api-suite-to-demo-pack/testplans/case-real-agent-all-lanes-auto.md`.
- [x] 1.3 Add and review `openspec/changes/move-houmao-server-agent-api-suite-to-demo-pack/testplans/case-real-agent-interrupt-recovery.md`.

## 2. Scaffold the Canonical Runner Surfaces

- [x] 2.1 Create `scripts/demo/houmao-server-agent-api-demo-pack/` with the required top-level layout: `README.md`, `run_demo.sh`, `.gitignore`, `agents/`, `inputs/`, `expected_report/`, `scripts/`, and `autotest/`.
- [x] 2.2 Add `scripts/demo/houmao-server-agent-api-demo-pack/autotest/run_autotest.sh` as a standalone harness with `--case <case-id>` selection, defaulting to `real-agent-all-lanes-auto`, and with result/log roots under the selected demo output directory.
- [x] 2.3 Add `scripts/demo/houmao-server-agent-api-demo-pack/autotest/helpers/` for shared shell logic that will be reused across the supported cases.
- [x] 2.4 Add pack-owned native selector assets under `agents/` and pack-owned tutorial inputs under `inputs/`, including prompt fixtures for canonical prompt and interrupt cases plus a minimal dummy-project template copied into run-owned lane workdirs.

## 3. Build Safe Demo Runtime Foundations

- [x] 3.1 Create a new helper package under `src/houmao/demo/houmao_server_agent_api_demo_pack/` with a typed CLI/module split for state models, command orchestration, provisioning, and reporting.
- [x] 3.2 Implement pack-owned output-root and persisted state handling, including default output roots under `scripts/demo/houmao-server-agent-api-demo-pack/outputs/`, copied run-owned workdirs, and stepwise reuse of the selected run.
- [x] 3.3 Implement explicit preflight and owned `houmao-server` startup logic that validates tools, credentials, pack assets, and output-root safety, starts an isolated server, injects the pack-owned `AGENTSYS_AGENT_DEF_DIR`, and applies bounded startup timeouts.
- [x] 3.4 Implement direct server-API lane provisioning for `claude-tui`, `codex-tui`, `claude-headless`, and `codex-headless`, including per-lane artifact recording and `/health` verification before lane admission.

## 4. Implement the Canonical Demo Path

- [x] 4.1 Implement `start`, `inspect`, `prompt`, `interrupt`, `verify`, `stop`, and `auto` command flows in the new helper package and expose them through `run_demo.sh`, with `auto` remaining the canonical unattended path.
- [x] 4.2 Implement server-owned inspect behavior that records and renders `GET /houmao/agents`, `GET /houmao/agents/{agent_ref}`, `/state`, `/state/detail`, `/history`, and optional TUI dialog-tail data from `/houmao/terminals/{terminal_id}/state`.
- [x] 4.3 Implement request validation artifacts for prompt submission across all lanes and interrupt submission through `POST /houmao/agents/{agent_ref}/requests`, including headless `/turns/*` follow-up when a turn handle is returned.
- [x] 4.4 Implement stop and cleanup behavior that tears down all launched lanes through `POST /houmao/agents/{agent_ref}/stop`, preserves cleanup evidence, stops the owned server, and marks persisted run state inactive.
- [x] 4.5 Implement `report.json`, `report.sanitized.json`, and expected-report comparison/snapshot tooling under `scripts/`, including sanitization of timestamps, paths, ids, and other non-deterministic values.
- [x] 4.6 Create the tracked `expected_report/report.json` for the canonical aggregate `auto` workflow and wire `verify --snapshot-report` to refresh it from sanitized content only.

## 5. Implement the HTT Cases and Harness Evidence

- [x] 5.1 Implement `autotest/case-real-agent-all-lanes-auto.sh` plus `autotest/case-real-agent-all-lanes-auto.md`, wiring the case through `autotest/run_autotest.sh` so it drives the canonical `auto` path, enforces per-phase timeouts, and writes result/log artifacts.
- [x] 5.2 Implement `autotest/case-real-agent-preflight.sh` plus `autotest/case-real-agent-preflight.md` so missing tools, credentials, selector assets, or unsafe output-root posture fail before any live startup.
- [x] 5.3 Implement `autotest/case-real-agent-interrupt-recovery.sh` plus `autotest/case-real-agent-interrupt-recovery.md` so the pack can validate tracked interrupt behavior and preserve post-interrupt state/history evidence.
- [x] 5.4 Ensure every implemented companion `autotest/case-*.md` is an independent step-by-step guide rather than a thin instruction to run the matching `.sh` script.

## 6. Add Regression Coverage, Docs, and Migration Cleanup

- [x] 6.1 Add focused automated coverage for the new helper package, harness dispatch, and report tooling so pack state handling, sanitization, case selection, and lane-selection/report contracts are regression-tested.
- [x] 6.2 Rewrite the new demo-pack `README.md` as a full tutorial-pack walkthrough with prerequisites, explicit command steps, inline critical inputs/outputs, verify instructions, snapshot guidance, and HTT/autotest guidance.
- [x] 6.3 Update reference docs and repository-owned workflow guidance so the canonical direct `houmao-server` managed-agent API validator points at `scripts/demo/houmao-server-agent-api-demo-pack/` instead of `tests/manual/`.
- [x] 6.4 Remove the old manual suite from the canonical workflow by deleting it or converting it into a temporary delegating shim, and ensure repository-owned docs no longer present `tests/manual/manual_houmao_server_agent_api_live_suite.py` as the primary operator entrypoint.
