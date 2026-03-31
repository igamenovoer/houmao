## 1. Overlay Resolution

- [x] 1.1 Add shared `HOUMAO_PROJECT_OVERLAY_DIR` resolution helpers in the project-overlay module, including absolute-path validation.
- [x] 1.2 Update project-overlay discovery and project-aware agent-definition resolution to honor `HOUMAO_PROJECT_OVERLAY_DIR` before nearest-ancestor `.houmao/houmao-config.toml` lookup.
- [x] 1.3 Update `houmao-mgr project init` and `houmao-mgr project status` to use the env-selected overlay directory and report the overlay-root source in status output.

## 2. Project-Aware Command Surfaces

- [x] 2.1 Update `houmao-mgr project` subcommands that require the active overlay so they resolve it from `HOUMAO_PROJECT_OVERLAY_DIR` before current-directory ancestor discovery.
- [x] 2.2 Update `houmao-mgr project mailbox ...` to resolve `<overlay-root>/mailbox` from the env-selected overlay directory and fail clearly when that selected overlay has no project config.
- [x] 2.3 Update project-aware build and launch resolution, including deprecated compatibility entrypoints, so `HOUMAO_PROJECT_OVERLAY_DIR` participates in the documented precedence contract.

## 3. Verification And Documentation

- [x] 3.1 Add or update unit tests for project init, project status, project mailbox, and project-aware agent-definition resolution under `HOUMAO_PROJECT_OVERLAY_DIR`, including relative-path and missing-overlay cases.
- [x] 3.2 Update CLI and getting-started docs to describe `HOUMAO_PROJECT_OVERLAY_DIR` as the direct overlay-directory override and keep `<cwd>/.houmao` as the default local overlay.
- [x] 3.3 Run the relevant targeted test suites and OpenSpec validation checks for the new overlay precedence behavior.
