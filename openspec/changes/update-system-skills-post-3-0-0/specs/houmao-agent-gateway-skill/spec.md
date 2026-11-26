# Spec Delta

## ADDED Requirements

### Requirement: Agent gateway covers plugin overrides, public dashboard, service/web routes, open-browser, and CCCC
`houmao-agent-gateway` SHALL document `--plugin-config-override INSTANCE=JSON` on `gateway attach`, public dashboard `GET /` and `/v1/endpoint` `admin_mode: open|keyed|unavailable`, `service`/`web` routes in `references/http-surface.md`, `agents single ... open-browser` alongside `gateway web-entry`, and `houmao-cccc` plugin CLI and `/v1/plugins/{instance}/*` routes (`delivery`, `chat`, `mail`).

#### Scenario: Gateway surfaces cover CCCC plugin routes, open-browser, and dashboard states
- **WHEN** a caller attaches gateway plugins, opens a local Kimi Web browser, inspects `GET /` or `/v1/endpoint`, or operates `houmao-cccc`
- **THEN** `lifecycle.md`, `web-entry.md`, `gateway-services.md`, and `http-surface.md` document `--plugin-config-override`, `open-browser` vs `web-entry`, `admin_mode: open|keyed|unavailable`, `/v1/control/{service,web}/*`, and `houmao-cccc` `/v1/plugins/{instance}/*`

### Requirement: Agent gateway tightens SKILL-MAIN.md and reminders.md prose
`houmao-agent-gateway` SHALL condense redundant Supported/Out-of-Scope/Missing-Input/Routing lists in `SKILL-MAIN.md` (~90 lines) and streamline the 111-line `commands/reminders.md` workflow while preserving every reminder parameter and ranking rule.

#### Scenario: Gateway entrypoint and reminders page stay concise
- **WHEN** a reviewer inspects `houmao-agent-gateway`
- **THEN** `SKILL-MAIN.md` avoids boilerplate repetition and `commands/reminders.md` preserves `one_off`/`repeat`, `--after-all`, `send_keys.ensure_enter`, and non-durability in fewer words

### Requirement: Agent gateway preserves attach/launch separation, foreground default, 60s web-entry, and env bans
`houmao-agent-gateway` SHALL preserve `## Actor Frame Gate`, attach/detach vs launch/stop separation, foreground auxiliary-window default (`--background` opt-in), 60-second single-use `web-entry` URL security, live-only ranked reminders, `mail-notifier` `appendix_text` preservation, and retired env var bans (`HOUMAO_GATEWAY_ATTACH_PATH`, `HOUMAO_GATEWAY_ROOT`).

#### Scenario: Retired gateway environment variables remain prohibited
- **WHEN** an agent needs the current gateway or mailbox endpoint
- **THEN** `houmao-agent-gateway` uses `gateway status` or `agents self mail resolve-live` and never uses retired `HOUMAO_GATEWAY_ATTACH_PATH` or `HOUMAO_GATEWAY_ROOT`
