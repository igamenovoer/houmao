# Refine Intention

## Preconditions

- `<loop-dir>/intention/` already exists.
- The user wants to revise loop source material.

## Inputs

Require:
- `<loop-dir>`
- the user's requested change or clarification

Read first:
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`
- any intention Markdown files directly relevant to the requested edit

## Actions

1. Preserve `intention/` as the editable source area.
2. Update `loop-overview.md` when the change affects the top-level objective, participants, lifecycle, or operating model.
3. Update or add focused freeform Markdown files when the change is more specific than the overview.
4. Keep unresolved choices explicit with `UNRESOLVED - <reason>`.
5. If an existing `execplan/` may now be stale, tell the user to run the `regenerate-execplan` operation.

## Constraints

- Do not rewrite user-authored freeform files into a rigid template.
- Do not edit generated `execplan/` files from this page.
- Do not require ADR files.
- Do not silently convert underspecified intention into unrelated domain policy.
