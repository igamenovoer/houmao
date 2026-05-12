## 1. Add shared scaffold resources

- [x] 1.1 Add a packaged Python scaffold generator under the v5 skill `scripts/` directory.
- [x] 1.2 Add packaged scaffold template assets for intention, execplan shell, execplan ADR, and final-doc starter files under the v5 skill `assets/` directory.

## 2. Route v5 authoring through the shared scaffold surface

- [x] 2.1 Revise `SKILL.md` and `agents/openai.yaml` so scaffold-producing routes point to the shared generator/templates as the authoritative scaffold source.
- [x] 2.2 Revise scaffold-producing authoring subskills to use shared scaffold profiles instead of page-local file creation prose.
- [x] 2.3 Revise validation and developer reference docs so expected starter files and package shape are described in terms of the shared scaffold surface.

## 3. Verify and close the change

- [x] 3.1 Validate the updated v5 skill package and targeted repo checks.
- [x] 3.2 Mark the completed tasks and confirm the change is ready for archive once implementation is done.
