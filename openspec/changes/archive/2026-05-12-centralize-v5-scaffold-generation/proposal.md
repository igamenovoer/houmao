## Why

The v5 loop skill currently describes scaffold creation in several subskills as prose, with repeated directory trees, starter files, and placeholder content. That makes scaffold behavior drift-prone: updating one place can leave other routes, staged generators, or validation expectations out of sync.

## What Changes

- Revise the v5 loop skill to use a Python scaffold generator instead of hand-authored per-page scaffold instructions.
- Add bundled Markdown and TOML template assets for intention scaffolds, execplan package shells, ADR stubs, manifests, and final support docs.
- Make `init`, `execplan-fast-forward`, and `execplan-step-by-step` route scaffold creation through the shared script/templates instead of describing separate ad hoc file creation flows.
- Update staged generation and validation guidance so scaffolded files are treated as centrally owned assets with explicit generation modes.
- **BREAKING** Remove the expectation that v5 scaffold structure is maintained only by prose instructions in multiple subskill pages; the script/template surface becomes the authoritative scaffold source.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `houmao-agent-loop-pairwise-v5-skill`: Centralize scaffold generation for intention and execplan package material through a Python script plus bundled templates, and require v5 scaffold-producing routes to use that shared surface.

## Impact

- Affected code: `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/`
- New assets likely under the v5 skill package: `scripts/` and `assets/` or `templates/`
- Affected behavior: `init`, `execplan-fast-forward`, `execplan-step-by-step`, and any staged page that currently describes scaffold file creation
- Affected validation/docs: OpenSpec spec for `houmao-agent-loop-pairwise-v5-skill`, skill routing text, and scaffold-shape validation guidance
