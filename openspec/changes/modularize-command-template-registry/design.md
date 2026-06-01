## Context

The command-template renderer currently lives in `src/houmao/srv_ctrl/commands/command_templates.py`. That module owns the public command-template functions, dataclasses, field builders, validation/rendering behavior, and every family declaration. The registry has grown to cover easy project authoring, low-level project agents, credentials, lifecycle commands, gateway commands, mailbox commands, and managed-agent mail fallback commands.

The desired source-of-truth remains Python code, not YAML. Python keeps the registry type-checkable, lets repetitive families such as credentials and mailbox commands use normal functions, and avoids introducing a YAML mini-language. The missing piece is modularity and a stable export surface for humans and tooling that want a YAML view of the registry.

## Goals / Non-Goals

**Goals:**
- Split the command-template source of truth into a dedicated package with family-specific Python modules.
- Keep the datamodel frozen and typed so template declarations continue to be validated before rendering.
- Preserve the existing `list`, `show`, and `render` CLI contracts.
- Add deterministic YAML export generated from the same template payloads as `show`.
- Keep family modules easy to scan and edit without hiding command ids behind excessive metaprogramming.

**Non-Goals:**
- Do not make YAML files the runtime source of truth.
- Do not add Jinja2, JSON Schema, or a template DSL for command-template declarations.
- Do not change the covered command-template ids or render semantics as part of the refactor.
- Do not move skill-owned loop scaffolds, workflow prompts, tours, or examples into command-template exports unless they map to a real `houmao-mgr` command surface.

## Decisions

### Create a `houmao.srv_ctrl.command_templates` package

Move reusable implementation from `src/houmao/srv_ctrl/commands/command_templates.py` into:

```text
src/houmao/srv_ctrl/command_templates/
  __init__.py
  models.py
  builders.py
  registry.py
  rendering.py
  export.py
  families/
    __init__.py
    project_easy.py
    project_agents.py
    credentials.py
    agents_lifecycle.py
    agents_gateway.py
    mailbox.py
    managed_agent_mail.py
```

`models.py` owns frozen dataclasses and literal value types. `builders.py` owns helper functions such as `field`, `flag`, `choice`, `clear`, `conflict`, and `template`. `families/*.py` owns template declarations. `registry.py` imports every family and assembles the stable id map. `rendering.py` owns intent loading, blocker detection, validation, and argv rendering. `export.py` owns deterministic YAML serialization.

Alternative considered: keep the single module and only add comments or section markers. This avoids import churn but does not solve navigation or reviewability.

### Keep a thin compatibility module for the existing command import path

Leave `src/houmao/srv_ctrl/commands/command_templates.py` as a thin wrapper that re-exports the public functions used by `internals.py` and tests, or update imports in one sweep and remove the old implementation. The preferred implementation path is a wrapper during the refactor because it reduces blast radius and preserves local import stability.

Alternative considered: move all imports immediately to the new package and delete the old module. This is cleaner after completion but creates a larger diff and makes bisecting harder.

### Keep code-first generation for repetitive families

Family modules may use ordinary Python loops and helper functions for repetitive surfaces such as:

- project/plain credential lanes
- Claude/Codex/Gemini credential-specific material fields
- mailbox/project-mailbox command pairs
- gateway reminders and TUI helpers
- managed-agent mail fallback verbs

The family modules must return concrete `CommandTemplate` objects, and registry tests must validate duplicate ids, stable id inventory, and target command surfaces. Generation should remain shallow enough that a reviewer can still find the declaration source for a template id.

Alternative considered: one Python object literal per concrete template. This maximizes explicitness but would duplicate many credential/mailbox/gateway definitions and invite drift.

### Add YAML export as a view, not a source

Add export functions that serialize the existing template payload shape:

```python
export_command_template_yaml(template_id: str) -> str
export_command_templates_yaml() -> str
```

The YAML output should preserve declaration order within each template payload, use deterministic template ordering for whole-registry export, and end with a newline. Exported YAML should be derived from `CommandTemplate.to_payload()` or an equivalent shared payload function so JSON `show` and YAML export remain equivalent in content.

Add CLI support under the existing internal command family:

```text
houmao-mgr internals command-templates export --id <template-id>
houmao-mgr internals command-templates export --all
```

The export command should write YAML to stdout and should not route through the JSON output engine when emitting YAML. If `--print-json` is used with export, the command may either return a JSON object containing the YAML string or reject the combination clearly; implementation should choose the least surprising behavior for existing output helpers.

Alternative considered: write generated YAML files into `src/` and load them at runtime. That undermines the code-first source of truth and creates generated-file churn.

## Risks / Trade-offs

- Import cycles between builders, models, and family modules could creep in -> keep models and builders dependency-light, and make families depend inward only.
- YAML export can drift from `show` output -> serialize from the same payload objects and add equivalence tests.
- Family-module generation can become too clever -> require tests that map selected ids to the expected source family and keep helper functions simple.
- A wrapper module can hide the new package boundary -> treat the wrapper as temporary compatibility glue and keep new tests importing the new package directly.

## Migration Plan

1. Introduce the new package and move dataclasses/builders/rendering code without changing behavior.
2. Move one family at a time into `families/*.py`, keeping the existing public functions green after each move.
3. Add YAML export helpers and CLI wiring.
4. Run focused command-template tests, lint, typecheck, and the broader unit suite.
5. After the new package is stable, optionally remove the compatibility wrapper in a later cleanup if no callers depend on it.
