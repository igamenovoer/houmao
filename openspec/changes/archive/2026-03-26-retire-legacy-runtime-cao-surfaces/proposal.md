## Why

The repository is still carrying two conflicting stories about runtime control. Supported pair and local-managed workflows already center on `houmao-server` and `houmao-mgr`, while multiple specs, docs, registry contracts, and runtime artifacts still preserve `houmao-cli`, standalone `houmao-cao-server`, gateway pointer env vars, and `attach.json`-style authority as if they were still first-class public surfaces.

That split is now blocking closure of the manifest-first gateway refactor. We need one explicit supported contract: manifest-owned authority, registry as a manifest locator, and `houmao-mgr` or `houmao-server` as the active operator surface. Legacy `houmao-cli` and standalone CAO-era surfaces should be revised or retired instead of continuing to shape new design work.

## What Changes

- Finish the manifest-first authority cutover for supported tmux-backed managed-agent flows, including gateway attach, gateway startup, relaunch, and registry lookup.
- Re-scope runtime-owned gateway artifacts so `manifest.json` is the only stable session authority, registry fallback is keyed by `runtime.manifest_path`, and old gateway pointer env vars no longer define the attach contract.
- Add the supported `houmao-mgr agents relaunch` contract for tmux-backed managed agents so gateway recovery and operator recovery do not route through build-time launch semantics.
- Downgrade or retire legacy runtime and CAO-era public surfaces, including standalone `houmao-cli` runtime-management guidance and standalone `houmao-cao-server`, so they no longer act as active design constraints.
- Revise repository identity and CLI guidance so active docs and specs treat `houmao-mgr` plus `houmao-server` as the primary public operator path.
- **BREAKING**: shared-registry and tmux-session discovery contracts stop treating `gateway_root`, `attach_path`, `AGENTSYS_GATEWAY_ATTACH_PATH`, and `AGENTSYS_GATEWAY_ROOT` as stable public authority.
- **BREAKING**: active repository guidance no longer presents `houmao-cli` as the primary runtime-management CLI for current workflows.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-gateway`: finish manifest-first gateway authority for supported flows, retire gateway pointer env vars as the stable attach contract, and narrow `attach.json` or equivalent gateway bootstrap artifacts to derived or internal roles instead of public authority.
- `brain-launch-runtime`: define tmux-backed relaunch and resume behavior around manifest-owned authority for supported surfaces and demote public standalone `houmao-cli` or raw CAO-era runtime-management paths to legacy or retired status.
- `agent-discovery-registry`: shrink registry discovery to authoritative identity plus runtime manifest location and retire required stable gateway pointer fields from the live record contract.
- `houmao-srv-ctrl-native-cli`: make `houmao-mgr` the explicit primary operator surface for supported managed-agent workflows, add the native relaunch contract, and move retained `houmao-cli` references into legacy-only guidance.
- `repo-identity-guidance`: revise the canonical active repository identity so current public guidance centers `houmao`, `houmao-server`, and `houmao-mgr` rather than teaching `houmao-cli` and `houmao-cao-server` as active first-class surfaces.
- `project-cli-identity`: retire the requirement that `houmao-cli` is the primary operator CLI and align project-facing CLI identity with the supported `houmao-mgr` plus `houmao-server` workflow.

## Impact

- Affected code: `src/houmao/agents/realm_controller/*`, `src/houmao/srv_ctrl/commands/agents/*`, `src/houmao/srv_ctrl/commands/managed_agents.py`, server-managed gateway paths, registry publication and lookup, and runtime attach or relaunch helpers.
- Affected contracts: `manifest.json`, gateway bootstrap and publication files under `<session-root>/gateway/`, tmux session env publication, shared-registry `record.json`, current-session attach, and managed-agent relaunch behavior.
- Affected docs and guidance: repo identity docs, CLI reference docs, pair workflow docs, legacy runtime docs, and retirement guidance for standalone CAO-era surfaces.
- Testing impact: unit and integration coverage will need updates for manifest-first attach and relaunch, registry lookup, gateway startup, deprecated legacy CLI failure behavior, and doc or help-surface assertions that now describe active versus retired operator paths.
