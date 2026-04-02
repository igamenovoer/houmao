## 1. Overlay Discovery Contract

- [x] 1.1 Add `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` parsing and validation to the shared project-overlay resolution layer, with `ancestor` as the default and `cwd_only` as the opt-in local mode.
- [x] 1.2 Implement ambient overlay discovery branching so `ancestor` keeps nearest-ancestor lookup within the Git boundary, `cwd_only` inspects only `<cwd>/.houmao`, and `HOUMAO_PROJECT_OVERLAY_DIR` still wins over ambient discovery.
- [x] 1.3 Carry the effective discovery mode through shared resolution results so downstream project-aware flows can report it without re-deriving policy.

## 2. Project-Aware Surfaces And Tests

- [x] 2.1 Update `houmao-mgr project status` and related project-aware wording or result payloads to surface the effective overlay discovery mode and the resulting root-selection behavior clearly.
- [x] 2.2 Add or update unit tests for default ancestor discovery, cwd-only local discovery, explicit overlay-dir precedence over cwd-only mode, and invalid discovery-mode env handling.
- [x] 2.3 Add or update integration or CLI-shape coverage so project-aware command outputs continue to match the documented selection and bootstrap contract under both discovery modes.

## 3. Documentation

- [x] 3.1 Update project-aware operations reference docs to describe `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`, its allowed values, and how it interacts with `HOUMAO_PROJECT_OVERLAY_DIR`.
- [x] 3.2 Update CLI reference and getting-started docs to reflect the revised ambient `.houmao` precedence contract, including the default `ancestor` behavior and the opt-in `cwd_only` mode.
