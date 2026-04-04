## Why

Houmao has already retired `.agentsys*` path families from maintained local defaults, but the live runtime contract still uses `AGENTSYS-` for canonical agent names and `AGENTSYS_*` for tmux session discovery, shared root overrides, mailbox bindings, CAO overrides, and operator-facing examples. That split keeps the product name and the runtime namespace out of sync, leaves stale `agentsys` terminology on active surfaces, and makes future cleanup harder because tests, docs, and specs continue to encode the old namespace as authoritative.

## What Changes

- **BREAKING** rename the canonical managed-agent namespace from `AGENTSYS-<name>` to `HOUMAO-<name>` on live supported surfaces.
- **BREAKING** rename Houmao-owned runtime, registry, mailbox, gateway, and launch environment variables from `AGENTSYS_*` to `HOUMAO_*`.
- **BREAKING** rename active CAO/runtime override env vars such as no-proxy preservation and parser preset pins into the `HOUMAO_*` namespace.
- Retire the last maintained lowercase/internal `agentsys` strings and metadata leftovers instead of preserving them as compatibility names.
- Update supported CLI, runtime, registry, mailbox, passive-server, and reference-doc contracts so the live surface is consistently Houmao-named.
- Keep archival OpenSpec history, resolved issue notes, and other clearly historical material out of scope for this rename.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-identity`: canonical agent naming, tmux session discovery pointers, and gateway attach pointers move from `AGENTSYS-*` / `AGENTSYS_*` to `HOUMAO-*` / `HOUMAO_*`.
- `agent-discovery-registry`: shared-registry naming and root override behavior use `HOUMAO-*` and `HOUMAO_*`.
- `agent-gateway`: current-session attach discovery uses `HOUMAO_MANIFEST_PATH`, `HOUMAO_AGENT_ID`, and related `HOUMAO_*` gateway pointers.
- `agent-mailbox-fs-transport`: mailbox-root env override moves from `AGENTSYS_GLOBAL_MAILBOX_DIR` to `HOUMAO_GLOBAL_MAILBOX_DIR`.
- `agent-mailbox-protocol`: default mailbox participant identities and examples use canonical `HOUMAO-*` principals and addresses.
- `brain-launch-runtime`: runtime launch, resume, mailbox, gateway, and env publication contracts move to `HOUMAO_*` names.
- `cao-claude-code-output-extraction`: the Claude Code parser-preset override env var moves to `HOUMAO_*`.
- `cao-loopback-no-proxy`: the no-proxy preservation env var moves to `HOUMAO_PRESERVE_NO_PROXY_ENV`.
- `cao-rest-client-contract`: CAO-compatible REST behavior uses `HOUMAO_PRESERVE_NO_PROXY_ENV`.
- `houmao-owned-dir-layout`: Houmao-owned override env vars and canonical naming examples use `HOUMAO_*` / `HOUMAO-*`.
- `passive-server-agent-discovery`: passive-server lookup canonicalizes `HOUMAO-*` names rather than `AGENTSYS-*`.
- `project-cli-identity`: project identity guidance standardizes the live runtime namespace on `HOUMAO_*` instead of preserving `AGENTSYS_*`.

## Impact

- Affected code:
  - `src/houmao/agents/realm_controller/agent_identity.py`
  - `src/houmao/owned_paths.py`
  - `src/houmao/agents/mailbox_runtime_support.py`
  - `src/houmao/agents/realm_controller/runtime.py`
  - `src/houmao/agents/realm_controller/gateway_storage.py`
  - `src/houmao/agents/realm_controller/gateway_service.py`
  - `src/houmao/agents/realm_controller/mail_commands.py`
  - `src/houmao/agents/realm_controller/backends/*.py`
  - `src/houmao/srv_ctrl/commands/*.py`
- Affected tests:
  - runtime identity, registry, mailbox, gateway, passive-server, and CLI contract suites that currently assert `AGENTSYS-*` or `AGENTSYS_*`
- Affected docs:
  - getting-started docs, CLI/reference docs, registry/gateway/mailbox docs, contributor guidance, and developer parsing docs that still document `AGENTSYS`
- Operational impact:
  - already-running sessions and local scripts that rely on `AGENTSYS-*` / `AGENTSYS_*` will need to relaunch or update to the new `HOUMAO-*` / `HOUMAO_*` contract
