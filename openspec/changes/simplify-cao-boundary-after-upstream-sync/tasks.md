## 1. CAO Boundary Compatibility

- [ ] 1.1 Update the CAO terminal boundary models and related tests so terminal `provider` parses as a forward-compatible string while terminal `status` remains a validated enum.
- [ ] 1.2 Keep the runtime CAO launch-time tool-to-provider mapping explicit, and add tests that parsed upstream provider ids do not automatically widen runtime launch support.
- [ ] 1.3 Make parser-scoped `shadow_only` validation explicit in the CAO runtime path, with tests covering explicit `cao_only` and unsupported `shadow_only` combinations.

## 2. Runtime and Operator Guidance Cleanup

- [ ] 2.1 Update CAO launcher and troubleshooting docs to remove the stale "workdir must be under home" guidance and describe `home_dir` as the CAO state/profile-store anchor.
- [ ] 2.2 Update interactive demo CLI/help/README text so `<launcher-home>/wktree` is described as a demo-owned isolation default rather than a CAO requirement.
- [ ] 2.3 Refresh any affected unit tests, fixtures, or golden text that currently assert the old provider enum surface or stale workdir guidance.

## 3. Verification

- [ ] 3.1 Run the focused CAO/runtime/demo test suites that cover boundary parsing, CAO-backed launch validation, and interactive demo surfaces.
- [ ] 3.2 Manually sanity-check the updated docs/examples against the synced upstream CAO behavior so the repo guidance no longer contradicts current upstream behavior.
