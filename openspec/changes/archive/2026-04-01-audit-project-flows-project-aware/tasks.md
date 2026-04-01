## 1. Split project command overlay access modes

- [x] 1.1 Add small shared helpers in `src/houmao/srv_ctrl/commands/project.py` for ensure-and-bootstrap versus resolve-only project overlay access, including clear missing-overlay errors for non-creating commands.
- [x] 1.2 Replace the remaining direct `_require_project_overlay()` call sites in `project.py` with the appropriate helper so maintained project commands no longer rely on the stale "run `project init` first" gate by default.

## 2. Audit maintained project command families

- [x] 2.1 Route maintained `houmao-mgr project agents tools ...` setup and auth commands through the correct overlay mode: ensure for `add` and `set`, resolve-only for `get`, `list`, and `remove`.
- [x] 2.2 Route maintained `houmao-mgr project agents roles ...` and `roles presets ...` commands through the correct overlay mode: ensure for `init`, `scaffold`, and preset `add`, resolve-only for `list`, `get`, and `remove`.
- [x] 2.3 Route maintained `houmao-mgr project easy specialist list/get/remove` and `project easy instance list/get/stop` through the shared resolve-only path while preserving the existing ensure behavior for specialist creation and instance launch.
- [x] 2.4 Refresh operator-facing help, docstrings, and error text in `project.py` so command descriptions and missing-overlay failures match the new bootstrap-versus-non-creating behavior.

## 3. Verify missing-overlay behavior

- [x] 3.1 Add focused unit coverage in `tests/unit/srv_ctrl/test_project_commands.py` for create flows that bootstrap the selected overlay and for inspection or removal flows that fail clearly without creating one.
- [x] 3.2 Add focused unit coverage for project easy specialist and instance inspection or stop flows to verify they remain non-creating when no overlay exists.
- [x] 3.3 Run the focused project command test targets and `openspec status --change audit-project-flows-project-aware` to confirm the follow-up change is implementation-ready.
