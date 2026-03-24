## 1. Retire obsolete CAO session demo packs

- [x] 1.1 Delete `scripts/demo/cao-claude-session/`, `scripts/demo/cao-codex-session/`, `scripts/demo/cao-claude-tmp-write/`, and `scripts/demo/cao-claude-esc-interrupt/`.
- [x] 1.2 Delete the active spec file `openspec/specs/cao-claude-demo-scripts/spec.md`.
- [x] 1.3 Update or remove any current non-archive docs, inventories, or checks that still directly reference those retired CAO session demo paths.

## 2. Retire the old CAO dual shadow-watch demo

- [x] 2.1 Delete `scripts/demo/cao-dual-shadow-watch/` and the supporting implementation under `src/houmao/demo/cao_dual_shadow_watch/`.
- [x] 2.2 Delete direct tests that exist only for the retired CAO dual shadow-watch implementation.
- [x] 2.3 Delete the active spec file `openspec/specs/cao-dual-shadow-watch-demo/spec.md` and update any current non-archive references that still point at the retired demo.

## 3. Validate the active surface after removal

- [x] 3.1 Run targeted searches to confirm the retired demo paths no longer appear in active specs, current docs, or live tests outside archive history.
- [x] 3.2 Verify the maintained migration target surfaces, especially `openspec/specs/houmao-server-dual-shadow-watch-demo/spec.md`, remain intact after the cleanup.
