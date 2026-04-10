# Prepare `runs/charter.template.toml`

Use this page when the bundle needs the minimal runtime handoff template.

## Workflow

1. Create `runs/charter.template.toml` under the bundle root.
2. Keep the template small and machine-shaped.
3. Include only the fields needed to identify the bundle and the later runtime route.
4. Keep the template separate from any live `start` request.

## Required Fields

- `run_id`
- `profile_id`
- `profile_version`
- `loop_kind`
- `master`
- `default_stop_mode`

## Guardrails

- Do not treat the template as a live start request.
- Do not move mutable runtime state into the template.
- Do not add fields that belong in Markdown guidance instead of simple metadata.
