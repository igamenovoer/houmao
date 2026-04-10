# `runs/charter.template.toml` Schema

Use this reference for the minimal runtime handoff template.

## Required Fields

- `run_id`
- `profile_id`
- `profile_version`
- `loop_kind`
- `master`
- `default_stop_mode`

## Rules

- Keep the template small and machine-shaped.
- Treat it as a template for later runtime activation, not as the live request itself.
- Do not add mutable runtime ledger or progress fields here.
