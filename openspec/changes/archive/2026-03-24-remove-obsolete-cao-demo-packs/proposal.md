## Why

Several older CAO demo packs under `scripts/demo/` are no longer needed, but active OpenSpec capabilities still require them to exist. That leaves the repository with obsolete demo assets, obsolete spec obligations, and direct references that will become misleading or broken once the packs are removed.

## What Changes

- Remove the obsolete demo packs `scripts/demo/cao-claude-session/`, `scripts/demo/cao-codex-session/`, `scripts/demo/cao-claude-tmp-write/`, `scripts/demo/cao-claude-esc-interrupt/`, and `scripts/demo/cao-dual-shadow-watch/`.
- Remove live implementation and test surfaces that exist only to support `cao-dual-shadow-watch/`, including its dedicated Python demo package and direct unit coverage.
- Retire the active capability requirements in `cao-claude-demo-scripts` that describe the removed CAO session demos.
- Retire the active capability requirements in `cao-dual-shadow-watch-demo` that describe the removed CAO dual shadow-watch pack.
- Update direct non-archive repo references so active docs, inventories, and checks no longer point at removed demo paths.
- Keep archived OpenSpec change history intact as historical record; do not rewrite archive material as part of this change.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `cao-claude-demo-scripts`: remove requirements tied to the retired `cao-claude-session`, `cao-codex-session`, `cao-claude-tmp-write`, and `cao-claude-esc-interrupt` demo packs.
- `cao-dual-shadow-watch-demo`: retire the old CAO dual shadow-watch capability and direct maintainers to the surviving `houmao-server-dual-shadow-watch-demo` flow instead.

## Impact

- Demo-pack assets under `scripts/demo/cao-claude-session/`, `scripts/demo/cao-codex-session/`, `scripts/demo/cao-claude-tmp-write/`, `scripts/demo/cao-claude-esc-interrupt/`, and `scripts/demo/cao-dual-shadow-watch/`
- Old CAO dual-watch implementation under `src/houmao/demo/cao_dual_shadow_watch/`
- Direct tests for the retired dual-watch implementation under `tests/unit/demo/`
- Active capability specs under `openspec/specs/cao-claude-demo-scripts/` and `openspec/specs/cao-dual-shadow-watch-demo/`
- Active documentation or inventories that still reference the retired demo paths
