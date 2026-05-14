## Why

The current pairwise loop skills stop at authored Markdown run plans, while the next loop model needs a general source-to-execution workflow that separates editable user intention from generated operational contracts. A new manual-only skill gives operators a deliberate entrypoint for complex loop authoring and execution without tying the model to any domain-specific workflow.

## What Changes

- Add a packaged Houmao-owned system skill named `houmao-agent-loop-pairwise-v5`.
- Make v5 manual-invocation-only because it creates and operates complex multi-agent loop plans.
- Define a required user-selected `<loop-dir>` as the root for v5 work.
- Define `<loop-dir>/intention/` as the editable, mostly freeform source area for user intention Markdown, with `README.md` and `loop-overview.md` as required entry files.
- Define `<loop-dir>/execplan/` as the generated execution package, using the current v5-style generated layout of `manifest.toml`, `specs/`, `skills/`, `agents/`, `harness/`, and `docs/`.
- Split v5 guidance into authoring subskills and execution subskills so the top-level skill remains an index/router instead of a monolithic instruction file.
- Require the implementation agent to invoke `$skill-creator` before creating or substantially updating the packaged v5 skill assets.
- Keep ADR discovery and ADR-driven generation out of the initial v5 contract; ADR support can be added later.
- Keep domain-specific material out of the skill requirements. Existing loop plans may be used as examples or fixtures, but packaged behavior is general.

## Capabilities

### New Capabilities
- `houmao-agent-loop-pairwise-v5-skill`: packaged manual v5 loop skill for creating editable intention material, generating execplans, and operating generated loop runs through subskills.

### Modified Capabilities

None.

## Impact

- Affected skill assets under `src/houmao/agents/assets/system_skills/`, including a new `houmao-agent-loop-pairwise-v5/` directory.
- Affected system-skill catalog and installation expectations so v5 can be discovered and installed like the existing pairwise skill family.
- Affected unit tests for packaged system-skill inventory, catalog ordering, and v5 skill content.
- Future implementation may add helper scripts under the skill directory, but no domain-specific generator behavior is part of this change.
