# Generate Execplan

Use this page when the user wants generated execution material from current v5 intention source.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`

Read the relevant files under `<loop-dir>/intention/`. Do not require `adrs/`.

## Generated Shape

Create or replace generated material under:

```text
<loop-dir>/execplan/
  manifest.toml
  specs/
  skills/
  agents/
  harness/
  docs/
```

Minimum responsibilities:
- `manifest.toml` indexes generated artifacts.
- `specs/` contains abstract loop contracts.
- `skills/` contains generated role/event or shared utility skills.
- `agents/` contains concrete agent bindings and prompt sources.
- `harness/` contains plan-local helper or execution surfaces when the loop needs deterministic state or validation.
- `docs/` contains generated human support views.

## Procedure

1. Confirm `<loop-dir>` and intention files exist.
2. Derive the execplan from intention source only.
3. Generate domain-specific objectives, roles, policies, evidence gates, and tools only when intention source states them.
4. Mark generated Markdown with a clear generated-source note or metadata block.
5. Keep generated skill files concise and progressively disclosed.
6. Preserve unresolved assumptions as explicit `UNRESOLVED - <reason>` entries.
7. Run the v5 `validate-execplan` operation before reporting completion.

## Boundaries

- Do not treat generated `execplan/` as editable source.
- Do not require ADR discovery.
- Do not copy CUDA/Hopper policies into unrelated loops.
- Do not create platform launch side effects from this page.
