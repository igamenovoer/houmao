## 1. Project CLI Definition Editing

- [ ] 1.1 Extend `houmao-mgr project agents roles` help and command wiring to add `set`, and extend `roles presets` to add `set`.
- [ ] 1.2 Implement `project agents roles get --include-prompt` plus `project agents roles set` for inline, file-backed, and clear-style prompt updates with explicit validation.
- [ ] 1.3 Implement `project agents roles presets set` with patch semantics for auth reference, skill membership, and prompt-mode updates while preserving unrelated preset blocks.

## 2. Packaged User-Control Skill

- [ ] 2.1 Add the packaged `houmao-manage-agent-definition` skill asset tree with `SKILL.md`, `agents/openai.yaml`, and action pages for `create`, `list`, `get`, `set`, and `remove`.
- [ ] 2.2 Author the new skill so it routes role and preset work to the supported `project agents roles ...` commands, uses the standard `houmao-mgr` launcher-resolution order, and keeps auth-bundle content mutation delegated to `houmao-manage-credentials`.
- [ ] 2.3 Add `houmao-manage-agent-definition` to the packaged `user-control` set and update shared system-skill inventory plumbing and CLI reporting for the expanded set membership.

## 3. Tests And Documentation

- [ ] 3.1 Add or update unit coverage for `project agents roles get --include-prompt`, `roles set`, and `roles presets set`, including explicit failure cases when no mutation was requested.
- [ ] 3.2 Update system-skill inventory and `houmao-mgr system-skills` tests to expect the new packaged skill in `user-control` and in CLI-default resolved installs.
- [ ] 3.3 Update operator-facing docs for the low-level `project agents roles ...` surface and the system-skills reference to describe the new definition-management workflow and its boundary with credential management.

## 4. Verification

- [ ] 4.1 Run the targeted project-command and system-skill test suites that cover the new role/preset editing verbs and packaged inventory reporting.
- [ ] 4.2 Validate the final OpenSpec change and confirm code, docs, and packaged-skill inventory all reflect the same low-level definition-management contract.
