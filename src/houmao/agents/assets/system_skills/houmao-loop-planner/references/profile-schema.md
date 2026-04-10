# `profile.toml` Schema

Use this reference for the minimal profile metadata file.

## Required Fields

- `profile_id`
- `version`
- `loop_kind`
- `master`
- `participants`
- `default_stop_mode`

## Rules

- Keep `profile.toml` small.
- Use TOML for identifiers, enums, and short lists only.
- Do not move long-form execution or participant guidance into `profile.toml`.
