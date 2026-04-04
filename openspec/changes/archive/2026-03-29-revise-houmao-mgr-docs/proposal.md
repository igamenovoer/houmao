## Why

`houmao-mgr` has accumulated significant CLI surface changes — `brains build` flags were renamed, the raw `realm_controller` module CLI was superseded by `houmao-mgr agents` as the primary operator surface, and Mermaid diagrams across several reference and internals docs still use old verb names (`start-session`, `send-prompt`, `stop-session`). The current docs contain actively wrong flag names, show the deprecated module CLI as the primary entry point in operator-facing reference pages, and use old abstract verbs in architecture diagrams that new users follow as instructions.

## What Changes

- **Corrected flag names** in `docs/reference/cli/houmao-mgr.md` brains build options table: `--recipe` → `--preset`, `--config-profile` → `--setup`, `--cred-profile` → `--auth`
- **Corrected example command** in `docs/reference/houmao_server_pair.md`: `--config-profile dev --cred-profile openai` → `--setup dev --auth openai`
- **Rewritten operator reference docs** (`agents/contracts/public-interfaces.md`, `registry/operations/discovery-and-cleanup.md`, `realm_controller_send_keys.md`): `houmao-mgr agents prompt/stop/gateway send-keys` becomes the primary surface; raw `python -m houmao.agents.realm_controller` examples move to a low-level access section
- **Added stalwart gap note** in `mailbox/operations/stalwart-setup-and-first-session.md`: documents that `--mailbox-transport stalwart` is not yet exposed via `houmao-mgr agents launch`, keeping raw module examples as the only access path
- **Updated Mermaid diagrams** across five ops/internals docs (`agents/operations/session-and-message-flows.md`, `gateway/operations/lifecycle.md`, `registry/internals/runtime-integration.md`, `agents/internals/state-and-recovery.md`, `mailbox/operations/common-workflows.md`): replace `start-session`/`send-prompt`/`stop-session` verbs with `houmao-mgr agents launch`/`agents prompt`/`agents stop`
- **Minor stale reference** in `system-files/roots-and-ownership.md`: `build-brain exposes --runtime-root` → `houmao-mgr brains build exposes --runtime-root`

## Capabilities

### New Capabilities

None. This change is a pure accuracy and surface-alignment pass on existing docs.

### Modified Capabilities

- `docs-cli-reference`: Add an explicit requirement that the `houmao-mgr brains build` options table must reflect current live CLI flag names (`--preset`, `--setup`, `--auth`) rather than old names (`--recipe`, `--config-profile`, `--cred-profile`)
- `docs-subsystem-reference`: Add a requirement that operator-facing reference pages within the agents, gateway, registry, and mailbox sections use `houmao-mgr agents` commands as the primary example surface, with raw `houmao.agents.realm_controller` module access relegated to a clearly-labelled low-level section

## Impact

Twelve documentation files under `docs/reference/` and `docs/getting-started/`. No source code changes. No API changes. No schema changes.
