# Topology Modes

## Purpose

Use this page when clarifying, generating, validating, or operating a pro loop with participant routes.

## Modes

Every generated pro execplan records one topology mode unless generation is blocked on an unresolved topology decision.

`tree-loop`:
- execution is a tree or forest of local-close handoffs;
- downstream participants reply to the immediate upstream participant for normal results;
- normal results do not bypass the immediate upstream;
- direct participant cycles are invalid unless normalized by `cycle-normalization.md`.

`generic-loop`:
- execution is a directed graph;
- routes may be non-tree and may contain cycles;
- downstream communication may move to participants other than the immediate upstream;
- process specs must define cycle control, dedupe or repeat-visit posture, and termination when cycles exist;
- predecessor-context needs are task-specific and follow `predecessor-context.md`.

## Aliases

Generate preferred values in new material:
- `tree-loop`;
- `generic-loop`.

Accept legacy aliases when validating or updating existing material:
- `tree-loop`: `pairwise-tree`, `pairwise-loop`, `pairwise`;
- `generic-loop`: `generic-graph`, `generic graph`.

Do not rewrite package names, skill handles, filenames, or historical examples only to remove an alias.

## Contract Placement

Record the selected mode in:
- `execplan/specs/collab/collab-overview.md`;
- `execplan/specs/collab/topology/topology.toml` when a machine-readable topology contract exists;
- generated docs or manifest notes when topology is intentionally trivial or omitted.

## Rules

- Do not infer `generic-loop` only because a diagram is cyclic; clarify when intent could mean tree-loop local-close execution.
- Do not force a master, coordinator, or root owner only because the topology is non-tree.
- Do not create synthetic participants while normalizing tree-loop topology.
- Do not treat diagram proximity as communication authority; routes must be explicit.
