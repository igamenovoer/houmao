## 1. Shared Naming And Runtime Identity

- [ ] 1.1 Add one shared helper in `src/houmao/agents/realm_controller/agent_identity.py` for deriving tmux session names as `<canonical-agent-name>-<agent-id-prefix>` with default prefix length 6, one-character collision-driven prefix extension, and optional occupied-session input; allow only thin tmux-facing wrappers elsewhere.
- [ ] 1.2 Switch runtime-owned start flows and the current tmux-backed backend allocators (`codex_headless`, `claude_headless`, `gemini_headless`, and `cao_rest`) to use the shared helper instead of `houmao-<session_id>` or legacy `AGENTSYS-<tool-role>` auto-names, retiring the old formula rather than carrying both algorithms in parallel.
- [ ] 1.3 Tighten runtime-owned manifest creation so tmux-backed sessions persist explicit `agent_name`, `agent_id`, and `tmux_session_name` without inferring canonical identity from the tmux handle.

## 2. Resolution And Discovery

- [ ] 2.1 Update tmux-local name resolution so canonical `AGENTSYS-<name>` inputs resolve to the unique live tmux session whose persisted metadata matches that canonical identity, while preserving exact-name legacy compatibility and avoiding reverse-parsing the tmux handle.
- [ ] 2.2 Ensure shared-registry publication, gateway/tmux environment publication, and resume/control validation continue to use the actual persisted `tmux_session_name` as the live transport handle.
- [ ] 2.3 Add or update runtime identity and manifest tests for suffixed tmux handles, explicit `--agent-id` overrides, ambiguity detection, one-character prefix extension on collision, and the negative case where canonical `agent_name` must not be inferred from a suffixed tmux handle.

## 3. Interactive Demo And Operator Surfaces

- [ ] 3.1 Update interactive demo persisted state and inspect rendering so `agent_identity` remains canonical while `session_name`, `tmux_target`, and attach commands use the actual tmux handle.
- [ ] 3.2 Update interactive demo startup recovery and stale-session cleanup to remove leftover tmux sessions associated with the canonical tutorial identity even when the live tmux handle includes an agent-id suffix, using persisted or discovered session metadata keyed by canonical identity plus exact-name legacy fallback rather than prefix-only tmux-name guesses.
- [ ] 3.3 Refresh the affected `docs/` runtime/demo reference pages, troubleshooting guidance, and manual helper scripts so they reflect the implemented tmux naming contract instead of assuming `tmux attach -t AGENTSYS-<name>`.
- [ ] 3.4 Run targeted tests for tmux identity resolution, manifest persistence, and interactive demo inspect/startup flows, including conservative cleanup behavior when similarly prefixed tmux names exist.
