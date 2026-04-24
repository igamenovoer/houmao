## 1. Registry safety fix

- [x] 1.1 Audit the project-skill registration/update path in `src/houmao/project/catalog.py` and identify every destructive helper call reached by `project skills add|set` and easy `--with-skill`.
- [x] 1.2 Change project-skill materialization so canonical replacement operates on lexical Houmao-managed paths under the active overlay instead of resolved symlink targets.
- [x] 1.3 Add or update ownership guards so destructive replacement and cleanup in the skill-registration flow can mutate only Houmao-managed canonical/projection paths.

## 2. Easy-specialist integration

- [x] 2.1 Ensure `project easy specialist create --with-skill` uses the hardened registry path without deleting or consuming caller-owned source directories.
- [x] 2.2 Ensure `project easy specialist set --with-skill` uses the hardened registry path without deleting or consuming caller-owned source directories.

## 3. Regression coverage

- [x] 3.1 Add unit coverage for `project skills set --mode copy` when the existing canonical skill entry is symlink-backed to the same caller-owned source directory.
- [x] 3.2 Add unit coverage for `project easy specialist create --with-skill` against an already-registered symlink-backed skill source and assert the source tree remains intact.
- [x] 3.3 Add unit coverage for `project easy specialist set --with-skill` against an already-registered symlink-backed skill source and assert the source tree remains intact.

## 4. Validation and related docs

- [x] 4.1 Update directly related CLI or guide text if needed so `--with-skill` is described as reading caller-owned source content while mutating only Houmao-managed overlay paths.
- [x] 4.2 Run the targeted project catalog and project command test coverage for the new source-safety regression paths.
