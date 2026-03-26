## 1. Manifest-First Resolution

- [ ] 1.1 Add a manifest-first current-session resolution path for tmux-backed sessions, including native headless, that prefers `AGENTSYS_MANIFEST_PATH` and falls back to `AGENTSYS_AGENT_ID` via shared-registry lookup.
- [ ] 1.2 Introduce a normalized manifest-derived session authority model for gateway attach and gateway runtime startup decisions.
- [ ] 1.3 Update pair-managed current-session attach flows to stop depending on `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`.

## 2. Manifest And Publication Contracts

- [ ] 2.1 Add the new manifest schema/version and persist normalized runtime, tmux, interactive, manifest-owned `agent_launch_authority`, and gateway-authority sections, including nullable `runtime.agent_pid`.
- [ ] 2.2 Keep backward-compatible manifest reads while migrating runtime resume and control code to the normalized manifest authority model.
- [ ] 2.3 Redefine `gateway/gateway_manifest.json` as derived outward-facing gateway bookkeeping and make attach actions force-overwrite it from manifest-derived authority.
- [ ] 2.4 Publish `gateway_pid` in `gateway_manifest.json` and stop treating `gateway_manifest.json` as the gateway process's mutable working store.
- [ ] 2.5 Keep the manifest secret-free while making tmux-backed relaunch consume manifest-owned relaunch posture plus the effective env published in the owning tmux session.

## 3. Runtime, Gateway, And Registry Integration

- [ ] 3.1 Update runtime gateway-capability publication to emit the new stable tmux discovery env contract (`AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_ID`) while preserving ephemeral live gateway bindings.
- [ ] 3.2 Update gateway runtime startup to derive behavior from the resolved manifest authority instead of loading `gateway_manifest.json` as the primary input, including native headless attach when no worker process is currently live.
- [ ] 3.3 Update shared-registry publication and lookup to use `runtime.manifest_path` as the fallback manifest locator without requiring stable gateway attach-path or gateway-root pointers.
- [ ] 3.4 Align `houmao_server_rest` attach and control handling with manifest-declared attach authority and runtime control authority.
- [ ] 3.5 Add the shared tmux-backed relaunch primitive and expose `houmao-mgr agents relaunch` so gateway-managed recovery and operator relaunch share the same implementation instead of build-time launch.
- [ ] 3.6 Keep window `0` reserved for the managed agent surface, including native headless console output, and make relaunch reuse that window without creating a replacement window; same-session gateway surfaces must still stay off window `0`.

## 4. Validation And Documentation

- [ ] 4.1 Add or update unit tests for manifest parsing, tmux discovery precedence, shared-registry fallback by `agent_id`, tmux-backed relaunch using manifest plus session env, nullable native headless `agent_pid`, and `gateway_manifest.json` regeneration semantics.
- [ ] 4.2 Add or update integration coverage for current-session pair attach, native headless between-turn attach, operator or gateway relaunch against reserved window `0`, runtime-owned gateway attach, and gateway startup using manifest-first authority.
- [ ] 4.3 Update reference documentation and operator guidance for the new tmux env contract, manifest authority model, tmux-backed relaunch contract, shared-registry fallback, and `gateway_manifest.json` bookkeeping role.
