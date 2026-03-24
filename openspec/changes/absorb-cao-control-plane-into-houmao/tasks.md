## 1. Control Core

- [ ] 1.1 Introduce a Houmao-owned CAO-compatible control-core package with service interfaces, live registries, tmux controller, provider-adapter boundary, and compatibility projection models.
- [ ] 1.2 Absorb the used CAO profile-store and install behavior into a Houmao-managed compatibility profile store plus compatibility inbox queue owned by the control core.

## 2. `houmao-server`

- [ ] 2.1 Replace child-CAO supervision and `/cao/*` proxy routing with direct `houmao-server` dispatch into the local control core.
- [ ] 2.2 Update server health, current-instance, install, and compatibility-route behavior to remove child-CAO port and child-home assumptions while preserving the supported public pair contract.
- [ ] 2.3 Keep Houmao watch, tracking, gateway, mailbox, and managed-agent registration flows authoritative on top of the new control core.
- [ ] 2.4 Preserve pair-managed `houmao_server_rest` gateway capability publication, tmux-published attach pointers, `gateway/run/current-instance.json`, and reserved window `0` behavior while replacing CAO underneath `/cao/*`.

## 3. `houmao-srv-ctrl` And Runtime Migration

- [ ] 3.1 Rework `houmao-srv-ctrl cao ...` commands to use Houmao-owned compatibility implementations instead of invoking external `cao`.
- [ ] 3.2 Preserve session-backed pair behavior for `launch`, `info`, `shutdown`, and `install`, and implement or absorb the remaining documented local compatibility helpers needed by `houmao-srv-ctrl`.
- [ ] 3.3 Add explicit migration failures for deprecated standalone CAO-facing `houmao-cli` paths that would create or control raw `cao_rest` sessions.
- [ ] 3.4 Retire `houmao-cao-server` so invocations fail fast with migration guidance to `houmao-server` and `houmao-srv-ctrl`.

## 4. Verification And Docs

- [ ] 4.1 Add parity and regression coverage for `/cao/*`, `houmao-srv-ctrl cao ...`, `houmao_server_rest` manifests, gateway attachability artifacts, profile install/store behavior, and compatibility inbox separation from Houmao mailbox/gateway.
- [ ] 4.2 Update docs, help text, and migration guidance so the supported operator path is the `houmao-server` plus `houmao-srv-ctrl` pair and deprecated standalone CAO surfaces are documented as retired.
