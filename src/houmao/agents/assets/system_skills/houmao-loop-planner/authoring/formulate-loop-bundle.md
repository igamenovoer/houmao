# Formulate A Loop Bundle

Use this page when the user has described what they want, but the operator still needs one valid loop bundle in a user-designated directory.

## Workflow

1. Start from the user's goal, constraints, named agents, preferred directory, and chosen loop kind.
2. Confirm the minimum control fields before drafting:
   - `loop_kind`
   - designated master
   - participant set
   - completion behavior
   - stop behavior
   - reporting posture
3. If any materially important field is still missing, ask only for that missing field instead of improvising it.
4. Create the bundle around the canonical files from `references/dir-structure.md`.
5. Keep the authored meaning Markdown-first:
   - `plan.md`
   - `participants.md`
   - `execution.md`
   - `distribution.md`
6. Keep TOML minimal by using only:
   - `profile.toml`
   - `runs/charter.template.toml`
7. Use `references/section-conventions.md`, `references/profile-schema.md`, and the local templates to keep the bundle consistent.
8. Render the top-level Mermaid graph through `authoring/render-loop-graph.md`.

## Authoring Rules

- Write the bundle in the user-designated directory.
- Keep the operator outside the execution loop.
- Keep the designated master explicit even when the same agent is obvious from context.
- Keep distribution as operator-owned work rather than a hidden planner-side delivery action.
- Do not write the authored bundle into `HOUMAO_JOB_DIR` or `HOUMAO_MEMORY_DIR`.

## Output Checklist

The finalized bundle should make these items easy to find:

- bundle root path
- loop kind
- master
- participants
- participant-local calling boundaries
- execution flow
- completion and stop behavior
- distribution instructions
- top-level Mermaid graph
