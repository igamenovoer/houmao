## 1. Resolver Diagnostics

- [ ] 1.1 Add shared managed-agent selector failure shaping in `src/houmao/srv_ctrl/commands/managed_agents.py` so local friendly-name misses can be reported explicitly instead of being overwritten by raw default pair-authority connection failures.
- [ ] 1.2 Extend local managed-agent lookup diagnostics to detect an exact unique tmux/session alias match and include the published `agent_name` or `agent_id` as corrective guidance without changing `--agent-name` selector semantics.
- [ ] 1.3 Update `resolve_managed_agent_target()` to compose local miss context, optional alias hints, and remote pair-unavailable notes into one actionable Click error for default local-plus-fallback resolution.

## 2. Shared Command Surface

- [ ] 2.1 Confirm the updated resolver path applies consistently to `agents`, explicit-target `agents gateway`, `agents mail`, and `agents turn` commands that use `resolve_managed_agent_target()`.
- [ ] 2.2 Preserve existing behavior for unique friendly-name matches, explicit `--agent-id` targeting, and explicit ambiguity failures while integrating the new miss diagnostics.

## 3. Test Coverage

- [ ] 3.1 Add unit coverage in `tests/unit/srv_ctrl/test_managed_agents.py` for local friendly-name miss plus pair-unavailable fallback, including the composed error message.
- [ ] 3.2 Add unit coverage in `tests/unit/srv_ctrl/test_managed_agents.py` for the exact tmux/session alias hint path and for the case where no unique alias hint is available.
- [ ] 3.3 Add representative CLI command tests in `tests/unit/srv_ctrl/test_commands.py` to verify that commands such as `agents show` or `agents prompt` surface the new actionable selector errors.

## 4. Verification

- [ ] 4.1 Run targeted unit tests for the managed-agent resolver and `houmao-mgr` command surfaces.
- [ ] 4.2 Verify `openspec status --change clarify-managed-agent-selector-errors` reports the change as apply-ready after artifact creation and implementation planning updates.
