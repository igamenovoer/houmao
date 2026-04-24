## 1. Owned-path mutation safety foundation

- [x] 1.1 Add shared owned-path mutation helpers for lexical containment checks, symlink-safe remove/replace flows, and explicit allowed-root declaration.
- [x] 1.2 Audit existing destructive filesystem helpers and route the project/catalog mutation paths through the shared owned-path safety layer where applicable.

## 2. Project catalog and migration hardening

- [x] 2.1 Harden project catalog content replacement and removal flows for auth profiles, memo seeds, setup snapshots, prompt overlays, and derived projections so they mutate only overlay-owned lexical paths.
- [x] 2.2 Harden `houmao-mgr project migrate --apply` so legacy import and cleanup paths preserve repo-owned source trees while still canonicalizing `.houmao/` content.

## 3. Credential and cleanup containment

- [x] 3.1 Harden managed credential bundle update/remove flows so symlink-backed managed artifacts are treated as artifacts, not recursive deletion targets, and caller-provided source files remain read-only.
- [x] 3.2 Harden `houmao-mgr` cleanup resolution and removal flows so escaped or symlink-targeted paths outside owned roots are rejected or unlinked safely without external deletion.

## 4. Registry and server authority containment

- [x] 4.1 Harden shared-registry record removal and stale cleanup so registry-owned lexical entries are removed without following symlinked record directories.
- [x] 4.2 Harden `houmao-server` managed headless authority cleanup so server-owned managed-agent artifacts remain contained to the managed-agent state tree.

## 5. Regression coverage and directly related docs

- [x] 5.1 Add targeted unit coverage for catalog, migration, credentials, cleanup, registry, and server-managed headless symlink safety scenarios.
- [x] 5.2 Update directly related CLI/help/reference text where filesystem ownership guarantees become part of the supported behavior.
