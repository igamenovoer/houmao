# Spec Delta

## MODIFIED Requirements

### Requirement: Tracked canonical presets for live role variants

Repository-owned filesystem seed trees SHALL provide secret-free named presets for documented role variants. The plain fixture GPU role SHALL include Claude default, Codex default, and Codex `api-compatible` variants. Presets SHALL identify role, tool, setup, selected skills, and optional auth by identifier only. They SHALL NOT require a personal credential name or the removed Yunwu fixture setup.

#### Scenario: Developer can locate tracked preset variants for the GPU demo role
- **WHEN** a developer inspects supported `gpu-kernel-coder` variants in `tests/fixtures/plain-agent-def/presets/`
- **THEN** the tree contains `gpu-kernel-coder-claude-default.yaml`, `gpu-kernel-coder-codex-default.yaml`, and `gpu-kernel-coder-codex-api-compatible.yaml`
- **AND THEN** those presets remain declarative and secret-free
- **AND THEN** model, endpoint, and effective credential selection can be supplied for the prepared run without editing tracked files
