# V5 Skill Developer Design Notes

These files are developer reference material for maintainers of `houmao-agent-loop-pairwise-v5`.

They are not part of skill execution. Do not route user requests through this directory, do not install these files as generated role skills, and do not treat them as operator-facing workflow pages. Runtime behavior belongs in the top-level `SKILL.md`, `agents/openai.yaml`, and the routed `subskills/` pages.

## Files

- `intent.md`: design intent, boundaries, and source-of-truth rules for v5.
- `execplan-contract.md`: intended shape and completeness expectations for generated execplans.
- `reference-execplan-patterns.md`: generic execplan patterns extracted from a mature generated reference package.
- `extension-guide.md`: guidance for revising or extending the packaged skill without blurring authoring, generation, and execution responsibilities.

## Maintenance Rule

When behavior changes, update the execution-facing skill files first, then update these notes to explain why the behavior exists and what future maintainers should preserve.
