## 1. Project CLI Prompt Inspection

- [x] 1.1 Implement `houmao-mgr project agents roles get --include-prompt` so full prompt text is opt-in while default role inspection remains summary-oriented.
- [x] 1.2 Add or update unit coverage for default `roles get` versus `--include-prompt`, including promptless-role behavior.

## 2. Packaged User-Control Skill

- [x] 2.1 Add the packaged `houmao-manage-agent-definition` skill asset tree with `SKILL.md`, `agents/openai.yaml`, and action pages for `create`, `list`, `get`, `set`, and `remove`.
- [x] 2.2 Author the new skill so it routes current low-level definition work to `project agents roles ...` and `project agents presets ...`, uses the standard `houmao-mgr` launcher-resolution order, and delegates auth-bundle content mutation to `houmao-manage-credentials`.
- [x] 2.3 Make the skill reject stale routing: no `project agents roles scaffold`, no `project agents roles presets ...`, and no direct filesystem editing under `.houmao/agents/`.

## 3. Inventory, Tests, And Docs

- [x] 3.1 Add `houmao-manage-agent-definition` to the packaged `user-control` set and update shared system-skill inventory plumbing and CLI reporting for the expanded set membership.
- [x] 3.2 Update system-skill inventory and `houmao-mgr system-skills` tests to expect the new packaged skill in `user-control` and in CLI-default resolved installs.
- [x] 3.3 Update operator-facing docs for the low-level `project agents` surface and the system-skills reference to describe the current role/preset/auth boundary and the new definition-management skill.

## 4. Verification

- [x] 4.1 Run the targeted project-command and system-skill test suites that cover `roles get --include-prompt`, packaged inventory reporting, and the new skill installation surface.
- [x] 4.2 Validate the final OpenSpec change and confirm all artifacts reference `project agents presets ...` instead of the retired `roles presets` shape.
