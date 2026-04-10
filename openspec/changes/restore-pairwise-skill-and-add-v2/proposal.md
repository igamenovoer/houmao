## Why

The current `houmao-agent-loop-pairwise` skill no longer matches the simpler stable surface that existed before the enriched pairwise rewrite. We need to restore the old pairwise contract under the original skill name while preserving the richer workflow as an explicitly versioned `houmao-agent-loop-pairwise-v2` skill so operators can choose either surface intentionally.

## What Changes

- Restore the pre-rewrite `houmao-agent-loop-pairwise` skill contract under the original skill name and asset path.
- Introduce `houmao-agent-loop-pairwise-v2` as the renamed home for the current enriched pairwise skill tree and lifecycle vocabulary.
- Keep both pairwise skills manual-invocation-only and require explicit user invocation by exact skill name.
- Update packaged system-skill catalog, `user-control` membership, install surfaces, docs, and tests to expose both skills.
- **BREAKING**: `houmao-agent-loop-pairwise` reverts from the current enriched lifecycle surface back to the earlier `start|status|stop` pairwise run-control contract; callers that depend on the enriched surface must switch to `houmao-agent-loop-pairwise-v2`.

## Capabilities

### New Capabilities
- `houmao-agent-loop-pairwise-v2-skill`: package the enriched pairwise authoring, prestart, and expanded run-control workflow under a distinct `-v2` skill name while keeping it manual-invocation-only.

### Modified Capabilities
- `houmao-agent-loop-pairwise-skill`: restore the original manual-invocation-only pairwise planning and `start|status|stop` run-control behavior under the stable `houmao-agent-loop-pairwise` name.
- `houmao-system-skill-installation`: package both pairwise skill variants in the maintained catalog and include both in the `user-control` named set and default resolved installs that expand `user-control`.
- `houmao-mgr-system-skills-cli`: make `list`, `install`, and `status` report both pairwise skill names and their resolved membership through `user-control`.
- `docs-system-skills-overview-guide`: document both pairwise variants and distinguish the stable pairwise surface from the enriched `-v2` surface.
- `docs-cli-reference`: update the system-skills CLI reference to enumerate both pairwise variants in the current packaged inventory and install selections.
- `docs-readme-system-skills`: update the README system-skills catalog and `user-control` set description to include both pairwise variants.

## Impact

- Affected assets: `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise*`, `catalog.toml`, and packaged skill metadata.
- Affected installer or CLI behavior: system-skill catalog resolution, `user-control` expansion, and visible install inventory under Codex, Claude, and Gemini homes.
- Affected docs: README system-skills section, getting-started system-skills overview, and CLI system-skills reference.
- Affected verification: catalog-driven skill-install tests, projected-home tests, and packaged-skill content assertions.
