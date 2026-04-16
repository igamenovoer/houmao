## 1. Skill Contract Text

- [x] 1.1 Update `llm-wiki-all-in-one/SKILL.md` so startup guidance, directory layout, operation steps, scaffold notes, and reference list use `README.md`.
- [x] 1.2 Update `llm-wiki-all-in-one/references/schema-guide.md` so it describes `README.md` as the wiki root schema and operating contract.
- [x] 1.3 Update remaining all-in-one reference and subskill docs so audit, article, log, and viewer deploy guidance mention `README.md` only.

## 2. Scaffold Behavior

- [x] 2.1 Update `llm-wiki-all-in-one/scripts/scaffold.py` to write the schema template to `README.md`.
- [x] 2.2 Update scaffold docstring, comments, console messages, log entry text, and next-step text to refer to `README.md`.

## 3. Verification

- [x] 3.1 Search the all-in-one skill deliverable and confirm `CLAUDE.md` has no remaining matches.
- [x] 3.2 Run the scaffold helper in a temporary directory and confirm it creates `README.md` and does not create `CLAUDE.md`.
- [x] 3.3 Validate the OpenSpec change with strict validation.
- [x] 3.4 Check parent and submodule Git status so the submodule commit pointer and OpenSpec artifacts are visible before commit.
