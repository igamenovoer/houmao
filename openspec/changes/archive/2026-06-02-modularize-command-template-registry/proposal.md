## Why

The command-template registry is now large enough that keeping data declarations, reusable family composition, validation, rendering, and CLI glue in one Python module makes template maintenance harder than it needs to be. Houmao should keep the templates code-first for type checking and composability, but split the registry into focused Python modules and provide a deterministic YAML export for inspection, documentation, and downstream tooling.

## What Changes

- Move command-template dataclasses, builders, family declarations, registry assembly, rendering, and export helpers into a dedicated `houmao.srv_ctrl.command_templates` package.
- Keep template declarations as Python source files grouped by command family rather than moving the runtime source of truth to YAML.
- Preserve the existing `houmao-mgr internals command-templates list|show|render` behavior and output shape.
- Add YAML export support for one template or the complete registry, generated from the same typed template models used by `show` and `render`.
- Add tests that prove the modular registry exposes the same ids and render behavior as before, and that exported YAML is deterministic and equivalent to the structured template payload.

## Capabilities

### New Capabilities

### Modified Capabilities
- `houmao-mgr-command-template-renderer`: command templates remain code-first but are organized as family modules and can be exported as deterministic YAML from the internal CLI.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/command_templates.py`, `src/houmao/srv_ctrl/commands/internals.py`, and a new `src/houmao/srv_ctrl/command_templates/` package.
- Affected tests: command-template unit tests and any CLI-shape tests covering `internals command-templates`.
- API compatibility: existing `list`, `show`, and `render` command contracts remain compatible; YAML export is additive.
- Dependencies: no new runtime dependency is required because PyYAML is already present in the project dependencies.
