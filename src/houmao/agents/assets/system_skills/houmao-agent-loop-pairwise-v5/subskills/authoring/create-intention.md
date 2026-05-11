# Init

## Preconditions

- User asked for `init`, invoked this skill without another operation or prompt, or wants to scaffold one loop directory.
- `create-intention` is a compatible alias.

## Inputs

Require:
- `<loop-dir>`

Optional:
- the user's loop intention, goal, or operating idea

Missing input rule:
- If `<loop-dir>` is missing, ask the user to provide an output directory and do not create files.

## Actions

1. Create `<loop-dir>/intention/`.
2. Create `<loop-dir>/intention/README.md` with:
   - a short explanation that `intention/` is editable source material,
   - a note that user edits are expected,
   - a pointer to `loop-overview.md` as the entrypoint,
   - a note that `execplan/` is generated from this source area.
3. Create `<loop-dir>/intention/loop-overview.md` as the human entrypoint.
4. If the user provided current intention, put it in `loop-overview.md` using clear headings, preserving uncertainty instead of inventing missing policy.
5. If the user did not provide current intention, scaffold `loop-overview.md` with editable placeholder headings for objective, participants, operating model, workspace expectations, constraints, and open questions.
6. Add additional Markdown files under `intention/` only when they make the intention easier to edit, such as `participants.md`, `workflow.md`, `workspace.md`, or `constraints.md`.

## Rules

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
