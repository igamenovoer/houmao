## 1. Policy Model And Schema Cleanup

- [x] 1.1 Replace the accepted operator-prompt mode vocabulary across parser, builder, runtime, and launch-policy models from `interactive|unattended` to `as_is|unattended`.
- [x] 1.2 Update resolved brain manifests, launch-plan metadata, typed provenance schemas, and validation logic so stored/runtime-visible policy values use the new semantics consistently and omitted policy resolves to unattended.

## 2. Authoring And Launch Surfaces

- [x] 2.1 Update low-level preset authoring commands and preset writers to accept/write `launch.prompt_mode` as `as_is|unattended`, default newly authored presets to explicit unattended posture, and remove `interactive` from operator-facing help text.
- [x] 2.2 Update `houmao-mgr project easy specialist create` to persist explicit unattended by default, persist `as_is` for `--no-unattended`, and expose stored launch posture through specialist inspection.
- [x] 2.3 Keep `houmao-mgr project easy instance launch`, `houmao-mgr agents launch`, and `houmao-mgr brains build` aligned with the new semantics so omitted or explicit policy values propagate into construction and runtime launch exactly once.

## 3. Runtime Launch-Policy Behavior

- [x] 3.1 Update launch-policy application so `unattended` still resolves strategy coverage and `as_is` bypasses unattended mutation, strategy selection, and no-prompt provenance.
- [x] 3.2 Update runtime diagnostics and failure reporting to describe `as_is|unattended` semantics rather than `interactive|unattended`, including fail-closed unattended compatibility errors.

## 4. Fixtures, Tests, And Documentation

- [x] 4.1 Rewrite repo-owned preset fixtures, unit/integration tests, and demo config that currently rely on `interactive|unattended` or omitted-as-pass-through semantics.
- [x] 4.2 Update operator-facing docs and OpenSpec capability docs to explain the new default unattended model, the meaning of `as_is`, and the breaking removal of explicit `interactive` policy values.
