## Why

Houmao's unattended startup contract for launched agents is currently underspecified. The immediate failure showed up on Codex, but the real issue is broader: Houmao needs one authoritative rule for all Houmao-launched agents, whether TUI or headless, so unattended startup does not depend on pre-existing tool state, copied setup defaults, or user-supplied low-level launch inputs.

## What Changes

- Define unattended launch as a Houmao-owned startup contract for all supported launched agents that force-canonicalizes strategy-owned runtime config/state and launch surfaces before provider start.
- Define setup projection as a baseline copy step: Houmao copies the selected setup bundle into the runtime home first, then applies unattended strategy overrides onto the runtime copy.
- Separate unattended compatibility from credential readiness and provider selection so launch-policy compatibility checks do not treat secret material as the definition of unattended support.
- Update project-easy specialist creation so the selected setup is explicit and persists into generated presets and stored specialist metadata instead of silently hardcoding `default`.
- **BREAKING**: For unattended Houmao-launched agents, strategy-owned runtime config/state keys and effective no-prompt launch surfaces override conflicting values from copied setup files and conflicting caller launch inputs.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `versioned-launch-policy-registry`: clarify that unattended strategies own specific runtime-home config/state keys and launch surfaces for all supported tools and backends, and that compatibility metadata is separate from credential readiness.
- `brain-launch-runtime`: require runtime construction to copy the selected setup bundle first, then apply unattended strategy overrides onto the runtime home before provider start for any supported Houmao-launched agent.
- `houmao-mgr-project-easy-cli`: require `project easy specialist create` to preserve the selected setup for project-easy specialists and carry it through generated presets and stored specialist metadata.

## Impact

- Affected code: `src/houmao/agents/launch_policy/*`, shared runtime-home/bootstrap helpers for supported tools, `src/houmao/agents/brain_builder.py`, `src/houmao/srv_ctrl/commands/project.py`, and related tests.
- Affected behavior: unattended runtime-home construction and launch-policy enforcement for Houmao-launched TUI and headless agents, plus project-easy specialist creation.
- Affected users: operators using unattended Claude Code, Codex, and future Houmao-launched agents, especially through project-easy flows.
