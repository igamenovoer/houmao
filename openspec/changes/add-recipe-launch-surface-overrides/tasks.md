## 1. Construction Inputs And Manifest Plumbing

- [x] 1.1 Rename the new concept to `launch_overrides`, add a typed secret-free `launch_overrides` model for recipe parsing and `BuildRequest.launch_overrides`, and replace `launch_args_override` directly with no deprecation window.
- [x] 1.2 Extend brain recipe loading, direct-build CLI input handling, and shared validation so recipe-backed and direct builds accept the same structured launch-overrides contract with `args` and `tool_params`.
- [x] 1.3 Bump resolved brain manifests to `schema_version = 2` and persist adapter-owned launch defaults, requested launch overrides, and construction-time provenance as separate structured fields without embedding secrets.
- [x] 1.4 Ensure the builder writes unresolved launch intent only: persist defaults, requested overrides, and provenance, but do not persist backend-resolved effective args or backend applicability guesses.

## 2. Launch-Overrides Resolver And Merge Semantics

- [x] 2.1 Add a shared Python `launch_overrides` package under `src/houmao/agents/` for typed models, merge logic, validation, and translation of launch-override requests into effective runtime launch settings, backed by declarative per-tool launch metadata rather than backend-only optional flag logic.
- [x] 2.2 Implement explicit precedence and merge behavior across adapter defaults, recipe overrides, direct-build overrides, launch policy, and backend-reserved protocol controls, including top-level section merge, per-key `tool_params` merge, and atomic `args` semantics.
- [x] 2.3 Extend tool-adapter launch metadata so supported optional launch params and their projections can be declared per tool, starting with Claude `include_partial_messages`, while making Gemini's v1 typed-tool-param set explicitly empty.
- [x] 2.4 Keep low-level `args` support as a bounded escape hatch for supported backends while preventing it from masquerading as a universally honored contract.

## 3. Runtime And Backend Refactor

- [x] 3.1 Refactor launch-plan composition to resolve effective launch overrides for the selected backend before provider start instead of assuming one flattened adapter-owned args list is always sufficient.
- [x] 3.2 Update headless and managed runtime backends to consume the resolved launch-overrides contract and typed provenance rather than reading only manifest `launch_args`, and keep backend `.py` launch assembly limited to protocol-required headless args.
- [x] 3.3 Enforce fail-closed behavior for unsupported backend combinations such as `cao_rest` and `houmao_server_rest` requests that cannot honor recipe-owned launch overrides and for requests that conflict with backend-reserved protocol args.
- [x] 3.4 Ensure runtime session metadata persists effective launch-overrides provenance so debugging can distinguish adapter defaults, recipe intent, direct overrides, launch-policy effects, and runtime-owned protocol controls.
- [x] 3.5 Reject legacy schema-version-1 brain manifests for this contract with explicit rebuild guidance rather than adding a temporary compatibility reader.

## 4. Concrete Provider Behavior

- [x] 4.1 Implement Claude headless support for the first typed launch param, `include_partial_messages`, through declarative tool-launch metadata and shared resolution without letting recipes override runtime-owned continuity flags.
- [x] 4.2 Add explicit negative coverage showing that Codex headless does not claim unsupported raw provider-partial streaming semantics while it remains based on `codex exec --json`.
- [x] 4.3 Add explicit negative coverage showing that `cao_rest` and `houmao_server_rest` reject launch-override requests they cannot honor instead of silently persisting misleading launch metadata.

## 5. Tests And Documentation

- [x] 5.1 Update the fixture tool-adapter YAML files under `tests/fixtures/agents/brains/tool-adapters/` to carry the declarative launch-metadata shape needed by the new contract.
- [x] 5.2 Add builder and recipe-loading tests for structured launch-overrides parsing, manifest writing, schema-version-2 output, and precedence between adapter defaults, recipe overrides, and direct-build overrides.
- [x] 5.3 Add runtime tests for backend-aware launch-overrides resolution, typed provenance, reserved-arg conflict rejection, schema-version-1 rejection, and unsupported-backend failure behavior.
- [x] 5.4 Update recipe, tool-adapter, builder, and runtime docs to describe the new default-plus-override ownership model, the declarative optional-launch metadata, the direct-build override input, the explicit “protocol args stay in backend code, optional behavior does not” rule, and the rebuild requirement for old brain homes.
