## 1. Construction Inputs And Manifest Plumbing

- [ ] 1.1 Add a typed secret-free `launch_surface` model for recipe parsing and `BuildRequest.launch_surface_override`, and retire the builder-only `launch_args_override` path in favor of that shared structure.
- [ ] 1.2 Extend brain recipe loading, direct-build CLI input handling, and shared validation so recipe-backed and direct builds accept the same structured launch-surface contract with `args` and `tool_params`.
- [ ] 1.3 Update resolved brain manifest models and writers to persist adapter-owned launch defaults, requested launch-surface overrides, and launch-surface provenance as separate structured fields without embedding secrets.
- [ ] 1.4 Preserve only unresolved launch intent in the built manifest so backend-specific applicability remains a runtime responsibility rather than a build-time guess.

## 2. Launch-Surface Registry And Merge Semantics

- [ ] 2.1 Add a shared Python launch-surface package under `src/houmao/agents/` for typed models, merge logic, validation, and translation of launch-surface requests into effective runtime launch settings, backed by declarative per-tool launch metadata rather than backend-only optional flag logic.
- [ ] 2.2 Implement explicit precedence and merge behavior across adapter defaults, recipe overrides, direct-build overrides, launch policy, and backend-reserved protocol controls.
- [ ] 2.3 Extend tool-adapter launch metadata so supported optional launch params and their projections can be declared per tool, starting with Claude `include_partial_messages`, and reject unknown or type-invalid `tool_params` explicitly.
- [ ] 2.4 Keep low-level `args` support as a bounded escape hatch for supported backends while preventing it from masquerading as a universally honored contract.

## 3. Runtime And Backend Refactor

- [ ] 3.1 Refactor launch-plan composition to resolve an effective launch surface for the selected backend before provider start instead of assuming one flattened adapter-owned args list is always sufficient.
- [ ] 3.2 Update headless and managed runtime backends to consume the resolved launch-surface contract and typed provenance rather than reading only manifest `launch_args`, and keep backend `.py` launch assembly limited to protocol-required headless args.
- [ ] 3.3 Enforce fail-closed behavior for unsupported backend combinations such as `cao_rest` requests that cannot honor recipe-owned launch overrides and for requests that conflict with backend-reserved protocol args.
- [ ] 3.4 Ensure runtime session metadata persists effective launch-surface provenance so debugging can distinguish adapter defaults, recipe intent, direct overrides, launch-policy effects, and runtime-owned protocol controls.

## 4. Concrete Provider Behavior

- [ ] 4.1 Implement Claude headless support for the first typed launch param, `include_partial_messages`, through declarative tool-launch metadata and shared resolution without letting recipes override runtime-owned continuity flags.
- [ ] 4.2 Add explicit negative coverage showing that Codex headless does not claim unsupported raw provider-partial streaming semantics while it remains based on `codex exec --json`.
- [ ] 4.3 Add explicit negative coverage showing that CAO-backed launches reject launch-surface requests they cannot honor instead of silently persisting misleading launch metadata.

## 5. Tests And Documentation

- [ ] 5.1 Add builder and recipe-loading tests for structured launch-surface parsing, manifest writing, and precedence between adapter defaults, recipe overrides, and direct-build overrides.
- [ ] 5.2 Add runtime tests for backend-aware launch-surface resolution, typed provenance, reserved-arg conflict rejection, and unsupported-backend failure behavior.
- [ ] 5.3 Update recipe, tool-adapter, builder, and runtime docs to describe the new default-plus-override ownership model, the declarative optional-launch metadata, the direct-build override input, and the explicit “protocol args stay in backend code, optional behavior does not” rule.
