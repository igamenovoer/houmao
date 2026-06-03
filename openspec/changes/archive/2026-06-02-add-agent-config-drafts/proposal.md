## Why

Agents currently use `houmao-mgr internals command-templates show|render` as the canonical way to author project-local agent configuration, but that surface mirrors the full CLI option grammar and returns far more schema metadata than the agent needs for ordinary config creation. The better abstraction for these workflows is a small set of typed config drafts: concrete YAML documents generated from Houmao's domain models with fixed lane/source/default values filled in by code.

## What Changes

- Add an internal `houmao-mgr internals config-drafts` command family that emits concrete YAML drafts for maintained agent-definition configuration shapes.
- Generate drafts from typed Houmao project/catalog data models and small input payloads instead of exposing a general dynamic template language or the full CLI option catalog.
- Cover the initial pre-launch configuration shapes that currently make agents load the largest command-template payloads:
  - easy specialist config draft
  - specialist-backed easy profile config draft
  - recipe-backed raw launch-profile config draft
- Keep command-template rendering available for CLI argv authoring, but stop treating it as the primary agent-facing surface for config-document authoring.
- Update packaged system-skill guidance for agent-definition workflows so agents call config drafts for YAML/config authoring and use command templates only for remaining command-execution workflows.
- **BREAKING**: Packaged Houmao skills will no longer instruct agents to call `command-templates show` before ordinary pre-launch config authoring. Existing CLI command-template commands may remain available, but they are no longer the preferred agent contract for these workflows.

## Capabilities

### New Capabilities
- `houmao-mgr-config-drafts`: Internal config-draft generation for agent-facing project configuration YAML, including draft listing, per-draft YAML emission, validation blockers, and explicit non-goals around dynamic template languages.

### Modified Capabilities
- `houmao-mgr-command-template-renderer`: Narrow command-template renderer responsibility to CLI argv rendering and maintainer inspection, not general project config YAML authoring.
- `houmao-manage-agent-definition-skill`: Route specialist, easy-profile, and raw launch-profile config authoring through `internals config-drafts` instead of command-template schema inspection.
- `houmao-memory-mgr-skill`: Route profile-owned memo-seed config authoring through the relevant config draft when the mutation belongs to a project profile document.

## Impact

- Affected CLI code: `src/houmao/srv_ctrl/commands/internals.py` and a new or adjacent internal config-draft package under `src/houmao/srv_ctrl/`.
- Affected project model code: project catalog/easy/launch-profile rendering helpers that already know how to produce semantic YAML views.
- Affected command-template code: documentation/tests may be updated to clarify that command templates remain argv-oriented and are not the config-draft source.
- Affected system-skill assets: `houmao-agent-definition` and profile/memo-related guidance should call the new config-draft workflow for pre-launch YAML authoring.
- Affected tests: unit tests for config-draft payloads, CLI shape tests for the new internals command family, and skill text tests that prevent regression to large `command-templates show` calls in config-authoring paths.
