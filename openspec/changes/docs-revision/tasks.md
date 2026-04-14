## 1. Spec Updates

- [x] 1.1 Apply readme-structure delta spec: update the section-ordering requirement to list steps 0–6 (adding step 1 "Drive with Your CLI Agent"), update project-init requirement to specify step 2, and add the new workspace-table requirement
- [x] 1.2 Apply docs-site-structure delta spec: add the landing-page intro and audience navigation requirement to the canonical spec

## 2. README.md Updates

- [x] 2.1 In step 2 (Initialize a Project), add `**memory/** — per-agent workspace roots, memo files, and scratch/persist lanes` to the `.houmao/` overlay bullet list
- [x] 2.2 In step 5 (Adopt an Existing Session), add a row to the capabilities table for `houmao-mgr agents workspace` commands (e.g., `path`, `memo show`, `tree`)
- [x] 2.3 In step 3 (Create Specialists & Launch Agents), add a one-line pointer to the [Managed Agent Workspaces](docs/getting-started/managed-memory-dirs.md) guide alongside the existing Easy Specialists and Launch Profiles guide references

## 3. docs/index.md Update

- [x] 3.1 Prepend a 2–3 sentence intro describing what Houmao is and who the site is for
- [x] 3.2 Add a "where to start" table immediately after the intro with rows for: installed user, from-source developer, contributor

## 4. Filename Fix

- [x] 4.1 Rename `DEVLEPMENT-SETUP.md` to `DEVELOPMENT-SETUP.md` (no content change)

## 5. quickstart.md Annotation

- [x] 5.1 Add a short callout at the top of `docs/getting-started/quickstart.md` stating that the guide uses `pixi run` (from-source checkout) and that installed users can drop the `pixi run` prefix and invoke `houmao-mgr` directly
