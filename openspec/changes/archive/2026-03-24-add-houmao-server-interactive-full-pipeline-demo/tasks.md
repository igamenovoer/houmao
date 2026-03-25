## 1. Demo pack scaffold and persisted state

- [x] 1.1 Create the new demo package under `src/houmao/demo/houmao_server_interactive_full_pipeline_demo/`, add the shell wrapper directory under `scripts/demo/houmao-server-interactive-full-pipeline-demo/`, and add the tracked compatibility-profile asset required for pair-managed startup
- [x] 1.2 Define strict demo state, startup payload, inspection payload, turn artifact, and verification/report models for the new pack around `provider`, `tool`, `agent_profile`, `variant_id`, delegated manifest pointers, and stable `agent_ref`
- [x] 1.3 Add standalone wrapper scripts and CLI wiring for `start`, `inspect`, `send-turn`, `interrupt`, `verify`, and `stop`

## 2. Pair-managed startup and delegated manifest discovery

- [x] 2.1 Implement demo-owned run-root provisioning, demo-owned working-tree setup, and a dedicated `houmao-server` lifecycle helper that launches `sys.executable -m houmao.server serve`, captures logs, and waits for health readiness for each run
- [x] 2.2 Implement demo-owned `houmao-srv-ctrl install` startup for the tracked compatibility profile, including default provider selection, explicit Codex override, and `--session-name` handling for `launch_alice.sh`
- [x] 2.3 Implement `houmao-srv-ctrl launch --agents ... --provider ...` startup with the demo-owned runtime-root environment, discover the resulting delegated runtime manifest, and persist the `HoumaoServerSectionV1` bridge data in demo state
- [x] 2.4 Persist `session_name` as the stable v1 `agent_ref`, confirm the pair-managed launch is already server-addressable without a second registration POST, and handle startup failure when delegated artifacts or server discovery are incomplete

## 3. Direct-server follow-up commands and verification

- [x] 3.1 Implement `inspect` over direct `houmao-server` managed-agent and tracked-terminal routes, keeping parser-derived dialog tail behind an explicit opt-in flag
- [x] 3.2 Implement `send-turn` and `interrupt` over `POST /houmao/agents/{agent_ref}/requests`, targeting the persisted v1 `agent_ref`, including artifact capture and bounded polling for server-tracked state changes
- [x] 3.3 Implement `stop` over direct `houmao-server` HTTP teardown for the recorded TUI session and handle stale-session cleanup safely
- [x] 3.4 Implement verification and sanitized reporting from accepted request records plus server-tracked state evidence rather than transcript text

## 4. Documentation and automated coverage

- [x] 4.1 Write the demo README with prerequisites, pair-managed startup workflow, route split, `launch_alice.sh` session-name behavior, and manual inspection guidance
- [x] 4.2 Add unit tests for pair-profile install input construction, delegated manifest discovery, state persistence, `session_name`-backed route targeting, absence of a second registration POST, optional inspect dialog-tail behavior, and stale-state handling
- [x] 4.3 Add integration coverage for the end-to-end install, launch, inspect, prompt, verify, and stop workflow of the new demo pack against a demo-owned `houmao-server`
