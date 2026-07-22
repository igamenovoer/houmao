# README Example Dialogues

Status: use cases drafted

## Purpose

Design the user↔AI example dialogues for the `readme-newcomer-revision` change. The README rewrite (tasks 3.3–3.5) needs concrete examples at three complexity levels that show the intended usage pattern: a human operator talks to their own CLI agent, which has Houmao system skills installed and drives `houmao-mgr` surfaces on the operator's behalf. These use cases are the source material for the Quick Start inline example and the later Agent-Driven Examples section.

## Artifacts

- [Use Cases](usecases/README.md)
- [ADRs](adrs/) — 0001: entrypoint-first prompting and the `houmao` trigger keyword

## Current Stage

`design-usecase` — three example dialogues (beginner / intermediate / advanced) covering the essential Houmao operator functionality. `feature-requirement.md` and `design/` are intentionally skipped: the feature requirement baseline lives in the OpenSpec change artifacts (`proposal.md`, `specs/readme-structure/spec.md`), and the interface contract lives in the system skills themselves.

## Related Context

- OpenSpec change: `openspec/changes/readme-newcomer-revision/` (proposal, design, specs, tasks)
- Exploration decisions D1–D5: `openspec/changes/readme-newcomer-revision/explore/design-choice/design-readme-narrative-sections.md`
- Skill ground truth: `skillset/runtime/public/`, `docs/getting-started/quickstart.md`, `docs/getting-started/system-skills-overview.md`, `examples/writer-team/`

## Open Questions

- Whether the README quotes these dialogues verbatim or in shortened form (decided at apply time, bounded by the spec's sentence-length and golden-path requirements).
