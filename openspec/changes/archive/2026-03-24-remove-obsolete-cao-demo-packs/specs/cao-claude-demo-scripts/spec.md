## REMOVED Requirements

### Requirement: Provide CAO-backed Claude demo packs
**Reason**: The repository is retiring the CAO session demo packs under `scripts/demo/cao-claude-tmp-write/` and `scripts/demo/cao-claude-esc-interrupt/`, along with the related `cao-claude-session` and `cao-codex-session` demo surfaces they were grouped with operationally.
**Migration**: Use maintained demo packs such as `scripts/demo/cao-interactive-full-pipeline-demo/` for supported CAO interactive walkthroughs, and do not expect the retired CAO session demo directories to remain present.

### Requirement: Demo packs have safe, explicit SKIP behavior
**Reason**: This requirement exists only to govern the startup behavior of the retired CAO session demo packs.
**Migration**: Supported demo packs keep their own startup and prerequisite contracts in their own active capabilities; no retained pack should rely on this retired capability for SKIP semantics.

### Requirement: Repo-owned CAO session demo response-extraction helpers do not treat `done.message` as authoritative reply text
**Reason**: The helper contract is specific to the retired `cao-claude-session`, `cao-codex-session`, and `cao-claude-tmp-write` demo implementations.
**Migration**: Shadow-aware turn verification continues to be specified in maintained demo capabilities such as `cao-interactive-full-pipeline-demo`; the retired helper paths should no longer be referenced.

### Requirement: `cao-claude-tmp-write` creates and verifies a runnable code file under `tmp/`
**Reason**: The underlying `scripts/demo/cao-claude-tmp-write/` pack is being removed from the maintained repository surface.
**Migration**: Do not expect a dedicated tmp-write CAO smoke demo to exist after this change. Use maintained interactive demos when CAO-backed walkthrough coverage is needed.

### Requirement: `cao-codex-session` remains valid under the default shadow-first runtime posture
**Reason**: The underlying `scripts/demo/cao-codex-session/` pack is being removed from the maintained repository surface.
**Migration**: Use maintained Codex-capable demo flows such as `scripts/demo/cao-interactive-full-pipeline-demo/` when interactive CAO walkthrough coverage is needed.

### Requirement: `cao-claude-esc-interrupt` demonstrates interrupt + recovery
**Reason**: The underlying `scripts/demo/cao-claude-esc-interrupt/` pack is being removed from the maintained repository surface.
**Migration**: Interrupt and recovery behavior, where still relevant, should be validated through maintained interactive demo flows rather than through the retired dedicated pack.
