## 1. Catalog And Installer Updates

- [x] 1.1 Rename the packaged named set `project-easy` to `user-control` in the system-skill catalog, installer constants, and any auto-install selection plumbing.
- [x] 1.2 Add `houmao-manage-credentials` to the `user-control` set and keep the separate `agent-instance` set behavior intact.
- [x] 1.3 Update system-skill CLI reporting so `list`, `install`, and `status` surface the renamed set and the expanded resolved skill inventory consistently.

## 2. New Packaged Skill Assets

- [x] 2.1 Create the packaged `houmao-manage-credentials` skill asset tree with `SKILL.md`, `agents/openai.yaml`, and action pages for `list`, `get`, `add`, `set`, and `remove`.
- [x] 2.2 Author the new skill so it reuses the standard `houmao-mgr` launcher-resolution order and routes only to `project agents tools <tool> auth ...` commands.
- [x] 2.3 Encode the explicit-input and safe-inspection guardrails in the new skill content, including redacted `auth get` handling and per-tool mutation-surface limits.

## 3. Tests And Documentation

- [x] 3.1 Update unit coverage for packaged system-skill catalog loading, install-state projection, and default-set resolution to expect `user-control` and `houmao-manage-credentials`.
- [x] 3.2 Update CLI-facing tests for `houmao-mgr system-skills` so list/install/status output reflects the renamed set and new skill membership.
- [x] 3.3 Update operator and developer docs that currently refer to the `project-easy` system-skill set so they use `user-control` and describe the new credential-management skill accurately.

## 4. Verification

- [x] 4.1 Run the targeted system-skill and CLI unit tests that cover catalog loading, projected skill installation, and `houmao-mgr system-skills` output.
- [x] 4.2 Verify the final packaged skill inventory, named sets, and auto-install selections remain internally consistent across specs, code, and docs.
