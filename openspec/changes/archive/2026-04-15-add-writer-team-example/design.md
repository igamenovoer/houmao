## Context

The `../agentsys2` workspace demonstrates a useful three-agent writing team, but it is a live Houmao project with initialized `.houmao/` state, mailbox data, memory directories, launch-profile projections, credentials, and generated story artifacts. This repository currently has no top-level `examples/` directory; runnable demos live under `scripts/demo/`, while the README already describes the writer-team pattern at a high level.

This change should preserve the reusable idea from `agentsys2` without copying runtime state. The example is documentation-like source material: prompt files, a pairwise loop plan, a start charter, and setup commands that a user can run to materialize their own local project state.

## Goals / Non-Goals

**Goals:**

- Add a clear `examples/writer-team/` template for a three-agent writing team.
- Use the supported `houmao-mgr project easy` workflow for specialists, profiles, and launches.
- Use relative output paths so the example works from any checkout.
- Show filesystem mailbox setup for pairwise delegation.
- Keep generated story artifacts and live runtime state out of source control.
- Align the example with the simplified managed memory model by omitting legacy memory configuration.
- Link the existing README story-writing section to the reusable example.

**Non-Goals:**

- Do not add a new loop runtime or CLI API.
- Do not add a fully automated CI demo under `scripts/demo/`.
- Do not embed credentials, fixture auth bundles, mailbox messages, runtime state, or generated story chapters.
- Do not preserve compatibility with old launch-profile fields copied from `agentsys2`.

## Decisions

### Template-first example under `examples/writer-team/`

Create a new top-level `examples/writer-team/` directory rather than copying `../agentsys2` wholesale or adding a `scripts/demo/` entry.

Rationale: the user asked for `examples/writer-team`, and the artifact is primarily an inspectable starting point. A runnable demo would require more machinery for credentials, cleanup, verification, and generated output management.

Alternative considered: add `scripts/demo/writer-team`. This better matches existing runnable demo conventions, but it makes the first version heavier and shifts the focus from teaching the pattern to validating automation.

### Commit source material, ignore materialized state

Commit prompt files, loop-plan files, README instructions, placeholder output directories, and ignore rules. Do not commit `.houmao/`, mailbox contents, memory directories, credentials, logs, or generated story documents.

Rationale: users need the reusable contract, not the source workspace's live state.

Alternative considered: commit a preinitialized `.houmao/` project. This would make the tree look immediately runnable, but it risks stale launch-profile state, accidental secrets, machine-specific paths, and old memory settings.

### Use relative paths and current memory behavior

The loop plan and README shall use paths relative to `examples/writer-team/`, such as `story/chapters/`, `story/characters/`, and `story/review/`. The example shall not configure `memory_binding`, `memory_dir`, or any old memory fields.

Rationale: the simplified memory subsystem is managed by Houmao at launch time, while the writing artifacts belong in the user-designated workspace directory.

Alternative considered: document explicit memory setup. That would distract from the writing-team use case and reintroduce the ambiguity the memory simplification removed.

### Keep orchestration pairwise and master-owned

The plan shall designate `alex-story` as the master and `alex-char` / `alex-review` as named workers. Workers close results back to the master and do not delegate further.

Rationale: this matches the proven `agentsys2` loop and the stable `houmao-agent-loop-pairwise` mental model.

Alternative considered: use pairwise-v2 routing packets or a generic loop. Those are useful for richer topologies but unnecessary for a three-agent chapter pipeline.

## Risks / Trade-offs

- Template examples can drift from CLI behavior -> include concrete commands and keep them on supported `houmao-mgr` surfaces.
- Adding a top-level `examples/` directory introduces a new documentation convention -> keep the first example narrow and link it from README so it has a clear purpose.
- Users may expect the example to run without credentials -> state that credentials/auth setup is operator-provided and intentionally not committed.
- Placeholder story directories may look empty -> include `.gitkeep` files and README text explaining that real chapters, profiles, and reviews are generated locally.
