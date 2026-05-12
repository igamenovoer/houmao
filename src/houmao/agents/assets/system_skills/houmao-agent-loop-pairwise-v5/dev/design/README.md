# Skill Developer Design Notes

These files are developer reference material for maintainers of `houmao-agent-loop-pairwise-v5`.

They are not part of skill execution. Do not route user requests through this directory, do not install these files as generated role skills, and do not treat them as operator-facing workflow pages. Runtime behavior belongs in `agents/openai.yaml`, the top-level `SKILL.md` router, the routed operation pages under `subskills/`, and the runtime reference pages under `subskills/reference/`.

## Runtime Reference Boundary

- `SKILL.md` should stay short: activation, required root, operation list, routing, and global constraints.
- `subskills/reference/` contains shared runtime guidance that invoking agents read from routed operation pages.
- `dev/design/` contains maintainer rationale and extension advice only.
- If a detail is needed during normal skill execution, put it in `subskills/reference/` or the relevant operation page, then keep `dev/design/` as the explanation of why that rule exists.

## Files

- `intent.md`: design intent, boundaries, and source-of-truth rules.
- `execplan-contract.md`: intended shape and completeness expectations for generated execplans.
- `reference-execplan-patterns.md`: generic execplan patterns extracted from a mature generated reference package.
- `extension-guide.md`: guidance for revising or extending the packaged skill without blurring authoring, generation, and execution responsibilities.

## Maintenance Rule

When behavior changes, update the execution-facing skill files first, then update these notes to explain why the behavior exists and what future maintainers should preserve.
