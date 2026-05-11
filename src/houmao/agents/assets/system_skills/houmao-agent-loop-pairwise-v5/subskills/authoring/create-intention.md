# Create Intention

Use this page when the user has selected `houmao-agent-loop-pairwise-v5`, provided a loop intention, and wants to initialize one loop directory.

## Inputs

Require:
- `<loop-dir>`
- the user's loop intention, goal, or operating idea

If `<loop-dir>` is missing, ask for it and do not create files.

## Procedure

1. Create `<loop-dir>/intention/`.
2. Create `<loop-dir>/intention/README.md` with:
   - a short explanation that `intention/` is editable source material,
   - a note that user edits are expected,
   - a pointer to `loop-overview.md` as the entrypoint,
   - a note that `execplan/` is generated from this source area.
3. Create `<loop-dir>/intention/loop-overview.md` as the human entrypoint.
4. Put the user's current intention in `loop-overview.md` using clear headings, preserving uncertainty instead of inventing missing policy.
5. Add additional Markdown files under `intention/` only when they make the intention easier to edit, such as `participants.md`, `workflow.md`, or `constraints.md`.

## Output

Report:
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`
- any additional freeform intention files created

## Boundaries

- Do not generate `execplan/` from this page.
- Do not require or create `adrs/`.
- Do not impose a strict schema on extra intention Markdown.
- Do not encode domain-specific policy unless it came from the user's intention.
