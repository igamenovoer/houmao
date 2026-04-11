## 1. Baseline and Existing Behavior

- [x] 1.1 Run focused baseline tests for managed prompt rendering and managed-header launch/profile behavior.
- [x] 1.2 Inspect current managed-header metadata payload shape in manifests and launch-profile payloads.
- [x] 1.3 Confirm existing `--managed-header` / `--no-managed-header` behavior on direct launch, explicit launch profiles, and easy profiles before changing section behavior.

## 2. Managed Header Section Model

- [x] 2.1 Add managed-header section identifiers for `identity`, `houmao-runtime-guidance`, `automation-notice`, `task-reminder`, and `mail-ack`.
- [x] 2.2 Add validation and normalization for section policy mappings and `SECTION=STATE` CLI inputs.
- [x] 2.3 Implement section decision resolution with precedence: one-shot override, stored profile policy, section default.
- [x] 2.4 Preserve whole-header policy as the outer gate so whole-header disable suppresses all sections.
- [x] 2.5 Split managed-header rendering into deterministic section renderers and include the automation notice text with the required uppercase prohibitions, the task reminder text, and the opt-in mail acknowledgement text.
- [x] 2.6 Update prompt layout metadata to include section tags and secret-free section decision information.

## 3. Profile Storage and Payloads

- [x] 3.1 Add additive project catalog storage for launch-profile managed-header section policy.
- [x] 3.2 Update launch-profile create/set persistence to store section policy mappings while treating omitted sections as inherited section-default values.
- [x] 3.3 Update launch-profile get/list payloads to report stored section policy without expanding omitted section-default decisions into stored values.
- [x] 3.4 Ensure existing profiles with no section policy render default-enabled sections and omit default-disabled sections when the whole managed header resolves to enabled.

## 4. CLI Surfaces

- [x] 4.1 Add repeatable `--managed-header-section SECTION=STATE` to `houmao-mgr agents launch` and forward it as a one-shot section override.
- [x] 4.2 Add repeatable `--managed-header-section SECTION=STATE` to `houmao-mgr project agents launch-profiles add`.
- [x] 4.3 Add `--managed-header-section SECTION=STATE`, `--clear-managed-header-section SECTION`, and `--clear-managed-header-sections` to `houmao-mgr project agents launch-profiles set`.
- [x] 4.4 Add repeatable `--managed-header-section SECTION=STATE` to `houmao-mgr project easy profile create`.
- [x] 4.5 Add `--managed-header-section SECTION=STATE`, `--clear-managed-header-section SECTION`, and `--clear-managed-header-sections` to `houmao-mgr project easy profile set`.
- [x] 4.6 Add repeatable `--managed-header-section SECTION=STATE` to `houmao-mgr project easy instance launch` and forward it as a one-shot section override.
- [x] 4.7 Add Click error coverage for unknown section names, unknown states, and conflicting clear/set combinations.

## 5. Launch and Relaunch Behavior

- [x] 5.1 Thread stored section policy and one-shot section overrides into `launch_managed_agent_locally()`.
- [x] 5.2 Persist managed-header section decision metadata in build manifests.
- [x] 5.3 Ensure relaunch of manifests without section metadata recomputes current section-default decisions.
- [x] 5.4 Ensure persisted whole-header disable decisions still suppress all sections during launch and relaunch.

## 6. Documentation

- [x] 6.1 Update the managed prompt header reference with the section model, section defaults, automation notice semantics, task reminder semantics, and mail acknowledgement semantics.
- [x] 6.2 Update the launch profiles guide with stored section policy examples and direct override behavior.
- [x] 6.3 Update the CLI reference for all section-level flags and supported section/state vocabularies.
- [x] 6.4 Update any system-skill or project-management skill docs that describe managed-header profile controls.

## 7. Verification

- [x] 7.1 Add or update unit tests for section resolution, section-default behavior, rendered automation notice text, rendered task reminder text, and rendered mail acknowledgement text.
- [x] 7.2 Add or update project command tests for launch-profile and easy-profile section-policy create/set/get flows.
- [x] 7.3 Add or update launch tests for direct one-shot section overrides and whole-header disable precedence.
- [x] 7.4 Run focused managed prompt header tests.
- [x] 7.5 Run focused project command and agents launch tests.
- [x] 7.6 Run Ruff on edited implementation, tests, and docs-relevant files.
- [x] 7.7 Run `openspec validate add-managed-header-section-controls --strict`.
