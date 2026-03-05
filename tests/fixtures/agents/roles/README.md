# Roles Repository

`agents/roles/` stores brain-agnostic role packages.

Each role package contains:

- `system-prompt.md` (required)
- `files/` (optional supporting files referenced by the prompt)

Roles are applied after a brain is constructed and the tool process has started.
