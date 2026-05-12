## 1. Wheelhouse Assets

- [x] 1.1 Add skill-bundled `.whl` assets for `jinja2`, `click`, `jsonschema`, and required dependencies under the v5 skill package.
- [x] 1.2 Add wheelhouse metadata documenting wheel filenames, package versions, provenance, and refresh instructions.

## 2. Harness Dependency Guidance

- [x] 2.1 Revise `execplan-harness` to teach use of `jinja2`, `click`, and `jsonschema` for generated harness features when those features are needed.
- [x] 2.2 Revise `execplan-harness` to require dependency detection through the intended harness interpreter, current interpreter, and applicable project dependency declarations.
- [x] 2.3 Revise `execplan-harness` to generate `execplan/harness/requirements.txt` and normal local `python -m pip install --target execplan/harness/vendor -r execplan/harness/requirements.txt` instructions when dependencies are missing or uncertain.
- [x] 2.4 Revise `execplan-harness` to document final offline fallback installation from the skill-bundled wheelhouse using `--no-index --find-links`.
- [x] 2.5 Revise harness guidance to generate local `sys.path` bootstrap before imports when `execplan/harness/vendor/` is used.

## 3. Validation And Design Docs

- [x] 3.1 Update `validate-execplan` to check dependency posture, requirements metadata, vendor directory posture, wheelhouse metadata, install diagnostics, and local import bootstrap.
- [x] 3.2 Update v5 developer design docs to explain the environment-first, local-pip-target, wheelhouse-final-fallback policy for generated harnesses.
- [x] 3.3 Update `agents/openai.yaml` or top-level skill routing text when needed so invoking agents know the harness dependency policy exists.

## 4. Verification

- [x] 4.1 Validate the updated v5 skill package.
- [x] 4.2 Run a small smoke check for a harness-local pip target install from the bundled wheelhouse or document why the wheelhouse smoke check cannot run.
- [x] 4.3 Run `git diff --check` and confirm the OpenSpec change is apply-ready.
