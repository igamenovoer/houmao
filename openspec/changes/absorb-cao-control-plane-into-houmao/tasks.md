## 1. Control Core

- [ ] 1.1 Introduce a Houmao-owned CAO-compatible control-core package with service interfaces, live registries, tmux controller, compatibility projection models, and a server-local compatibility transport that preserves the current `/cao/*` route-handler seam.
- [ ] 1.2 Implement v1 provider-adapter coverage for the current pair compatibility launch surface (`kiro_cli`, `claude_code`, `codex`, `gemini_cli`, `kimi_cli`, `q_cli`) and document any intentional retirement explicitly rather than narrowing provider support implicitly.
- [ ] 1.3 Absorb the used CAO profile-store and install behavior into a Houmao-managed compatibility profile store, including the minimum used install slice: agent-source resolution, required profile validation/frontmatter handling, provider-specific materialization, and profile metadata indexing.
- [ ] 1.4 Keep the pair-facing `HoumaoServerRestSession -> CaoRestSession -> CaoRestClient(path_prefix="/cao")` seam for v1, but override or extract the startup and profile-store hooks that currently require `cao-server` on `PATH` or caller-managed local CAO profile-store assumptions.
- [ ] 1.5 Audit `/cao/terminals/{terminal_id}/inbox/messages` usage and implement the smallest compatibility-only inbox behavior that preserves the supported route contract while remaining separate from Houmao mailbox and gateway state.

## 2. `houmao-server`

- [ ] 2.1 Replace child-CAO supervision and external `/cao/*` proxy routing with local `houmao-server` dispatch into the control core through the server-local compatibility transport, preserving current route-side hooks such as created-terminal sync, delete handling, and prompt-submission bookkeeping.
- [ ] 2.2 Update root health and current-instance behavior to remove child-CAO port and child-home assumptions while preserving `service="cli-agent-orchestrator"` plus `houmao_service="houmao-server"` on the supported pair health surface.
- [ ] 2.3 Move pair install behavior onto the Houmao-owned compatibility profile store and return explicit server-owned failures for install validation, source-resolution, or materialization errors.
- [ ] 2.4 Keep Houmao watch, tracking, gateway, mailbox, and managed-agent registration flows authoritative on top of the new control core.
- [ ] 2.5 Preserve pair-managed `houmao_server_rest` gateway capability publication, tmux-published attach pointers, `gateway/run/current-instance.json`, and reserved window `0` behavior while replacing CAO underneath `/cao/*`.

## 3. `houmao-srv-ctrl` And Runtime Migration

- [ ] 3.1 Rework `houmao-srv-ctrl cao ...` commands to use Houmao-owned compatibility implementations instead of invoking external `cao`.
- [ ] 3.2 Preserve session-backed pair behavior for `launch`, `info`, `shutdown`, and `install`, keep the current pair launch provider identifiers explicit across `launch` and `cao launch`, and implement or absorb the remaining documented local compatibility helpers needed by `houmao-srv-ctrl`.
- [ ] 3.3 Add CLI-layer migration failures for deprecated standalone CAO-facing `houmao-cli` paths that would create or control raw `cao_rest` sessions, while keeping internal `CaoRestSession` usage available for parity or transitional pair machinery.
- [ ] 3.4 Retire `houmao-cao-server` so invocations fail fast with migration guidance to `houmao-server` and `houmao-srv-ctrl` before config parsing, process launch, or launcher-artifact mutation, and update the installed command wiring accordingly.

## 4. Verification And Docs

- [ ] 4.1 Add parity and regression coverage for `/cao/*`, `houmao-srv-ctrl cao ...`, the preserved root `/health` compatibility fields, `houmao_server_rest` startup without raw `cao-server` requirements, gateway attachability artifacts, profile install/store behavior, provider-surface preservation, and compatibility inbox separation from Houmao mailbox/gateway.
- [ ] 4.2 Update docs, help text, and migration guidance so the supported operator path is the `houmao-server` plus `houmao-srv-ctrl` pair, the preserved provider surface and root-health compatibility behavior are documented, and deprecated standalone CAO surfaces are documented as retired.
