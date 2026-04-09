## 1. Native CLI Error Boundary

- [ ] 1.1 Update the `houmao-mgr` top-level wrapper to catch the realm-controller runtime base error family and render clean CLI error text without Python tracebacks.
- [ ] 1.2 Preserve the existing non-zero exit behavior for expected operator-facing runtime failures while leaving truly unexpected non-runtime exceptions untouched.

## 2. Local Managed-Agent Resume Error Normalization

- [ ] 2.1 Update the registry-backed local controller resume helper to wrap stale tmux-backed resume failures with managed-agent contextual `ClickException` text.
- [ ] 2.2 Ensure `agents stop`, `agents prompt`, `agents interrupt`, and `agents relaunch` all inherit the same clean local stale-target failure behavior through shared target resolution.

## 3. Regression Coverage

- [ ] 3.1 Add unit coverage for registry-backed local managed-agent resolution when controller resume raises a runtime-domain error rather than `SessionManifestError`.
- [ ] 3.2 Add native CLI regression coverage proving stale tmux-backed managed-agent failures exit non-zero and render explicit error text without Python tracebacks.
