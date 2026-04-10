# Bundle Directory Structure

Use this reference for the canonical loop bundle layout.

## Canonical Layout

```text
<user-designated-loop-dir>/
  plan.md
  participants.md
  execution.md
  distribution.md
  profile.toml
  runs/
    charter.template.toml
```

## Rules

- `plan.md` is the canonical human entrypoint.
- Keep the bundle Markdown-first.
- Keep TOML limited to `profile.toml` and `runs/charter.template.toml`.
- Keep the bundle rooted in a user-designated directory.
