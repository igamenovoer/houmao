# Init

## Read First

- `../reference/scaffold-surface.md`
- `../reference/system-input-questions.md`

## Preconditions

- User asked for `init`, invoked this skill without another operation or prompt, or wants a new loop directory initialized with project context.

## Inputs

Require:
- `<loop-dir>`

Optional:
- the user's loop intention, goal, or operating idea;
- user-provided project context;
- an explicit project root to inspect.

Missing input rule:
- If `<loop-dir>` is missing, ask with `Required: <loop-dir>` and an `Optional` section for project root, project context hints, naming preferences, or `none for this step`; do not create files.

## Actions

1. Use the packaged scaffold generator with the `intention-init` profile to materialize:
  - `<loop-dir>/intention/README.md`;
  - `<loop-dir>/intention/loop-overview.md`;
  - `<loop-dir>/intention/project-context.md`.
2. Resolve the project-context source:
  - if the user prompt names an explicit project root, inspect that root;
  - otherwise inspect around `<loop-dir>`.
3. Detect whether the selected location is inside a project:
  - prefer `git -C <path> rev-parse --show-toplevel` when available;
  - otherwise look upward for project indicators such as `.git/`, `pyproject.toml`, `pixi.toml`, `package.json`, `packages.json`, `conanfile.py`, `conanfile.txt`, `CMakeLists.txt`, `Cargo.toml`, `go.mod`, `pom.xml`, `build.gradle`, `Makefile`, `README.md`, `docs/`, or similar project manifests.
4. Use lightweight reads and searches only:
  - inspect nearby manifests, README/docs, top-level directories, and obvious command definitions;
  - do not run builds, tests, package installs, network commands, or heavyweight scans.
5. Fill `<loop-dir>/intention/project-context.md` with concise bullets:
  - detected project root or repository identity;
  - project type and main tooling;
  - relevant build, test, runtime, or package commands when discoverable from manifests or docs;
  - important contracts, APIs, docs, directories, or domain constraints;
  - user-provided project context when supplied;
  - `UNRESOLVED - <reason>` for important context that is likely needed but unclear.
6. If no project is detected and no user project context is supplied, leave `project-context.md` with placeholder bullets and note that no surrounding project was detected.
7. If the user provided current intention, revise `loop-overview.md` after scaffolding with clear headings, preserving uncertainty instead of inventing missing policy.
8. If the user did not provide current intention, keep `loop-overview.md` as editable source placeholders.
9. Add additional Markdown files under `intention/` only when they make the intention easier to edit.

## Rules

- Treat the packaged scaffold generator and `assets/scaffolds/` templates as the authoritative starter source for these files.
- Treat detected or user-provided project context as helpful orientation, not as a substitute for loop intent.
- Keep `project-context.md` concise; it should help generated loop artifacts integrate with the surrounding codebase without replacing project documentation.
- Preserve user-provided uncertainty.
- Keep intention files editable and freeform.
- Treat `execplan/` as future generated output, not scaffold output.

## Output

Report:
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`
- `<loop-dir>/intention/project-context.md`
- any additional freeform intention files created

## Constraints

- Do not generate `execplan/` from this page.
- Do not require or create `adrs/`.
- Do not impose a strict schema on extra intention Markdown.
- Do not encode domain-specific policy unless it came from the user's intention, user-provided project context, or detected project artifacts.
- Do not run heavyweight project analysis, tests, builds, dependency installation, or network lookup during init.
