# Create Intention

## Read First

- `../reference/scaffold-surface.md`
- `../reference/system-input-questions.md`

## Preconditions

- User asked for `create-intention` or wants to scaffold the editable intention files without project-context discovery.

## Inputs

Require:
- `<loop-dir>`

Optional:
- the user's loop intention, goal, or operating idea

Missing input rule:
- If `<loop-dir>` is missing, ask with `Required: <loop-dir>` and an `Optional` section for current intention text, naming preferences, or `none for this step`; do not create files.

## Actions

1. Use the packaged scaffold generator with the `intention-create` profile to materialize `<loop-dir>/intention/README.md` and `<loop-dir>/intention/loop-overview.md` from the shared templates.
2. If the user provided current intention, revise `loop-overview.md` after scaffolding with clear headings, preserving uncertainty instead of inventing missing policy.
3. If the user did not provide current intention, keep the scaffold headings and placeholder bullets as editable source.
4. Add additional Markdown files under `intention/` only when they make the intention easier to edit, such as `participants.md`, `workflow.md`, `workspace.md`, or `constraints.md`.

## Rules

- Treat the packaged scaffold generator and `assets/scaffolds/` templates as the authoritative starter source for these files.
- Preserve user-provided uncertainty.
- Keep intention files editable and freeform.
- Treat `execplan/` as future generated output, not scaffold output.

## Output

Report:
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`
- any additional freeform intention files created

## Constraints

- Do not generate `execplan/` from this page.
- Do not require or create `adrs/`.
- Do not impose a strict schema on extra intention Markdown.
- Do not encode domain-specific policy unless it came from the user's intention.
