## Why

`houmao-srv-ctrl` reads like a narrow server-control utility, but the current CLI owns a broader pair-management surface: pair-native managed-agent commands, the explicit `cao` compatibility namespace, local brain construction, and local registry maintenance. Renaming it now to `houmao-mgr` makes the public product boundary clearer before more scripts, docs, and operator habits harden around a misleading name.

## What Changes

- **BREAKING** Rename the public pair-management CLI from `houmao-srv-ctrl` to `houmao-mgr`.
- Update the supported pair boundary from `houmao-server + houmao-srv-ctrl` to `houmao-server + houmao-mgr` everywhere the live product contract, migration guidance, tests, demos, and repo-owned docs describe the current CLI.
- Rename the explicit compatibility namespace examples from `houmao-srv-ctrl cao ...` to `houmao-mgr cao ...` while preserving the current command-family shape and pair-owned compatibility behavior.
- Update pair-native managed-agent command examples and help text to use `houmao-mgr agents ...`, `houmao-mgr brains build ...`, and `houmao-mgr admin cleanup-registry ...`.
- Align stale live references that still describe the old top-level `agent-gateway` surface so the renamed management CLI consistently documents `agents gateway attach` as the supported pair-owned attach path.
- Keep the current internal Python package layout under `houmao.srv_ctrl` for now unless a later change explicitly decides to rename internal module paths too.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: rename the pair-owned gateway attach CLI contract to `houmao-mgr agents gateway attach` and remove stale live references to the retired top-level gateway command shape.
- `brain-launch-runtime`: update fail-fast migration guidance and pair-managed launch references to point operators to `houmao-mgr`.
- `cao-server-launcher`: update retired-launcher migration guidance to point operators to `houmao-server` plus `houmao-mgr`.
- `houmao-cao-control-core`: rename the preserved pair launch surface and compatibility references from `houmao-srv-ctrl` to `houmao-mgr`.
- `houmao-server`: rename the supported replacement-pair contract from `houmao-server + houmao-srv-ctrl` to `houmao-server + houmao-mgr`.
- `houmao-server-dual-shadow-watch-demo`: rename the demo's required pair CLI and command examples to `houmao-mgr`.
- `houmao-server-interactive-full-pipeline-demo`: rename the demo's required pair CLI and command examples to `houmao-mgr`.
- `houmao-srv-ctrl-cao-compat`: redefine the public CAO-compatible service-management CLI contract around the new `houmao-mgr` binary name while preserving the explicit `cao` namespace and current pair behavior.
- `houmao-srv-ctrl-native-cli`: redefine the native pair-management command tree around the new `houmao-mgr` binary name and update the preferred pair-native command examples.

## Impact

- Affected code includes the package script entry in `pyproject.toml`, CLI help/prog-name wiring under `src/houmao/srv_ctrl/`, user-facing migration guidance, and demo/automation code that checks for or invokes the public binary name.
- Affected docs include `README.md`, `docs/reference/**`, `docs/migration/**`, demo READMEs under `scripts/demo/**`, and other repo-owned operator guidance that currently names `houmao-srv-ctrl`.
- Affected verification includes unit tests for the pair CLI help surface plus any script or demo checks that currently require `houmao-srv-ctrl` on `PATH`.
