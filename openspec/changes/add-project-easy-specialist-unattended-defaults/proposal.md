## Why

Houmao's current operator-prompt policy vocabulary is misleading for an automation-first system. `interactive` is treated as the pass-through mode, but the real intent is not "show an interactive UI"; it is "leave provider startup as-is and do not inject unattended policy." That naming leaks the opposite of what most Houmao users actually want, because the primary target workflows are managed automation runs where unattended startup is the default expectation.

This change started from `project easy` specialist defaulting, but that surface exposed a broader repository-wide policy mismatch. The system should default to unattended behavior across its build and launch seams, reserve one explicit opt-out for raw provider startup, and align presets, build requests, manifests, launch-policy provenance, runtime diagnostics, and high-level `project easy` authoring around the same intent model.

## What Changes

- Keep the existing policy key names, but change the allowed mode values repository-wide from `interactive|unattended` to `as_is|unattended`.
- Redefine `as_is` to mean "do not inject unattended launch behavior; use the raw provider startup posture."
- Change the default policy to `unattended` when declarative or direct build inputs omit an explicit prompt mode.
- Make `houmao-mgr project easy specialist create` persist explicit unattended posture by default for supported tools, with `--no-unattended` persisting `as_is`.
- Update low-level preset authoring and launch-facing CLI surfaces so `--prompt-mode` / operator-prompt inputs use `as_is|unattended` and no longer use `interactive`.
- Update built brain manifests, launch-plan metadata, session provenance, runtime validation, diagnostics, and tests/docs to use the new semantics consistently.
- Treat existing explicit `interactive` policy values as obsolete and require migration to `as_is` rather than carrying a long-term alias.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-easy-cli`: easy specialists default to unattended posture, `--no-unattended` persists `as_is`, and instance launch honors the stored specialist launch payload.
- `houmao-mgr-project-agents-roles`: low-level preset authoring uses `launch.prompt_mode` values `unattended|as_is` and defaults authored presets to unattended posture.
- `component-agent-construction`: declarative presets, direct build inputs, and resolved manifests use the new `as_is|unattended` operator-prompt policy semantics, with omitted policy resolving to unattended.
- `houmao-mgr-agents-launch`: preset-backed local launches preserve the new policy vocabulary, including unattended-by-default behavior when a preset omits prompt mode.
- `brain-launch-runtime`: runtime launch planning, strategy resolution, provenance, and failure behavior align with the new `as_is|unattended` policy semantics.

## Impact

- Affected code:
  `src/houmao/agents/definition_parser.py`, `src/houmao/agents/brain_builder.py`, `src/houmao/agents/launch_policy/{cli,engine,models}.py`, `src/houmao/agents/realm_controller/{launch_plan,boundary_models}.py`, `src/houmao/srv_ctrl/commands/{agents/core.py,brains.py,project.py}`, and `src/houmao/project/catalog.py`.
- Affected schemas and persisted/runtime-visible state:
  resolved brain manifests, session-manifest boundary schemas, launch-plan schemas, typed launch-policy provenance, preset YAML payloads, and project catalog launch payloads.
- Affected operator surfaces:
  `houmao-mgr project easy specialist create`, `houmao-mgr project agents roles presets add`, related low-level role scaffold/init commands, `houmao-mgr brains build`, and preset-backed `houmao-mgr agents launch`.
- Affected tests and fixtures:
  parser, builder, launch-policy, runtime, CLI, and fixture preset coverage that currently assumes `interactive|unattended` or omitted-as-pass-through semantics.
- Affected documentation and specs:
  OpenSpec capability docs, launch/runtime docs, troubleshooting docs, and operator examples that currently describe `interactive` as the non-unattended mode.
