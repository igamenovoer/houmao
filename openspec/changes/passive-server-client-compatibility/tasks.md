## 1. Passive server compatibility surface

- [ ] 1.1 Add a passive-server compatibility projection layer that builds `HoumaoManagedAgentIdentity`, `HoumaoManagedAgentStateResponse`, `HoumaoManagedAgentDetailResponse`, and `HoumaoManagedAgentHistoryResponse` from passive discovery, observation, and managed headless state.
- [ ] 1.2 Add `managed-state`, `managed-state/detail`, and `managed-history` service methods and HTTP routes without changing the existing observation route contracts.
- [ ] 1.3 Ensure passive-server-managed headless compatibility views surface live prompt-admission, interruptibility, last-turn, and history data, with explicit failures when required headless state is unavailable.

## 2. Pair-authority client support

- [ ] 2.1 Add a shared pair-authority client protocol and factory that probes `/health` and returns either `HoumaoServerClient` or a new `PassiveServerClient`.
- [ ] 2.2 Implement `PassiveServerClient` methods for lifecycle, discovery-based identity resolution, managed state/detail/history, prompt/interrupt/stop, gateway status/request, mail follow-up, and headless turn operations.
- [ ] 2.3 Normalize passive-server response payloads into the existing `HoumaoManagedAgent*` and `HoumaoHeadless*` models consumed by pair-facing code.

## 3. CLI and runtime integration

- [ ] 3.1 Update `srv_ctrl` common helpers and `houmao-mgr server` commands to accept `houmao-passive-server` as a supported pair authority.
- [ ] 3.2 Update `srv_ctrl` managed-agent command helpers to use the pair-authority client protocol, preserve registry-first behavior, and keep passive-server gateway attach/detach on the local-authority path.
- [ ] 3.3 Update gateway-managed headless runtime code to resolve managed clients through the pair-authority factory when `managed_api_base_url` points to a passive server.

## 4. Validation and operator guidance

- [ ] 4.1 Add passive-server tests for managed compatibility routes covering both observed TUI agents and passive-server-managed headless agents.
- [ ] 4.2 Add client and `houmao-mgr` tests for passive pair detection, server status/stop, managed-agent state/show flows, headless turn flows, and same-host gateway attach/detach fallback.
- [ ] 4.3 Add gateway-service tests for passive `managed_api_base_url` handling and update operator-facing guidance for Step 7 side-by-side validation on an alternate passive-server port.
- [ ] 4.4 Run the relevant `pixi run` lint and test commands for passive server, `srv_ctrl`, and gateway integration coverage.
