# Roles Repository

`agents/roles/` stores brain-agnostic role packages.

Each role package contains:

- `system-prompt.md` (required)
- `files/` (optional supporting files referenced by the prompt)

Roles are applied after a brain is constructed and the tool process has started.

Use lightweight roles such as `mailbox-demo` for narrow mailbox/runtime-contract turns in copied dummy projects. Use heavyweight roles such as `gpu-kernel-coder` when the scenario intentionally exercises broad repository-scale engineering behavior.
