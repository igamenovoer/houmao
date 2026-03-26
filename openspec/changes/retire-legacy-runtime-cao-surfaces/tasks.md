## 1. Manifest-First Runtime Authority

- [x] 1.1 Finish the manifest-first resolver flow for tmux-backed attach, resume, and relaunch so supported readers prefer `AGENTSYS_MANIFEST_PATH`, fall back to `AGENTSYS_AGENT_ID`, and resolve `runtime.manifest_path` from the shared registry.
- [x] 1.2 Update tmux-backed manifest writes and readers to treat normalized manifest authority as the supported source of truth for attach, control, and relaunch rather than legacy duplicated backend state.
- [x] 1.3 Change supported tmux session env publication to keep `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_ID` as the stable discovery contract and retire `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT` from active publication or supported use.

## 2. Gateway Artifact And Recovery Cleanup

- [x] 2.1 Rework gateway attach and startup to derive supported authority from `manifest.json` and to treat `gateway_manifest.json` as derived outward-facing bookkeeping only.
- [x] 2.2 Re-scope `attach.json` and related gateway bootstrap files as internal runtime artifacts only, and remove supported external readers that still treat them as public attach authority.
- [x] 2.3 Wire gateway-managed recovery to the shared tmux-backed relaunch primitive so recovery reuses the existing built home and window `0` instead of build-time launch behavior.

## 3. Native CLI And Relaunch Surface

- [x] 3.1 Add `houmao-mgr agents relaunch` with current-session and explicit managed-agent targeting for tmux-backed managed sessions.
- [x] 3.2 Update `houmao-mgr agents` help, selector handling, and managed-agent command wiring so `relaunch` is part of the supported native command family.
- [x] 3.3 Keep deprecated standalone `houmao-cli` or raw CAO-era runtime-management entrypoints failing with explicit migration guidance instead of silently remaining parallel supported paths.

## 4. Registry And Identity Contract Cleanup

- [x] 4.1 Remove required shared-registry gateway pointer fields such as `gateway_root` and `attach_path`, and keep `runtime.manifest_path` plus optional live gateway connect metadata as the supported discovery contract.
- [x] 4.2 Update active repo identity guidance, CLI help, and shipped docs so current workflows teach `houmao-mgr` and `houmao-server` as the supported operator surfaces.
- [x] 4.3 Move remaining `houmao-cli` and standalone `houmao-cao-server` references into explicit migration, legacy, or retirement guidance instead of active workflow documentation.

## 5. Verification

- [x] 5.1 Add or update unit coverage for manifest-first resolver behavior, registry fallback by `agent_id`, and legacy pointer retirement.
- [x] 5.2 Add integration coverage for pair-managed current-session gateway attach, native headless between-turn attach, and tmux-backed relaunch through `houmao-mgr agents relaunch`.
- [x] 5.3 Add regression coverage for deprecated standalone CLI failure behavior and for active help or docs surfaces that should no longer present `houmao-cli` or `houmao-cao-server` as current defaults.
