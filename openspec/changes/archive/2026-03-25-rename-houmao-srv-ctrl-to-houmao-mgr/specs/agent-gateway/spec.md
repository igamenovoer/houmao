## MODIFIED Requirements

### Requirement: Pair-owned gateway attach for managed `houmao_server_rest` sessions supports explicit and current-session targeting
The system SHALL expose `houmao-mgr agents gateway attach` as the pair-owned gateway attach surface for pair-managed tmux-backed TUI sessions whose runtime backend is `houmao_server_rest`.

When called with positional `<agent-ref>`, the command SHALL resolve the target through the Houmao managed-agent identity namespace and SHALL execute attach through the managed-agent gateway attach route rather than through raw `cao` or raw runtime CLI semantics.

When called without `<agent-ref>`, the command SHALL require execution inside the target agent's tmux session, SHALL discover the current tmux session as the attach context, SHALL read stable gateway attachability pointers from the current tmux session environment, SHALL require those pointers to resolve to a readable `houmao_server_rest` attach contract, SHALL treat that contract's persisted `api_base_url` and `backend_metadata.session_name` as the authoritative server and managed-agent route target for this mode, and SHALL refuse the attach when those envs are missing, stale, ambiguous, identify a non-`houmao_server_rest` session, or fail to resolve exactly one managed agent on that persisted server.

`houmao-mgr` SHALL NOT require the user to address raw `cao_rest` or child-CAO topology in order to attach a gateway for pair-managed sessions, and current-session attach SHALL NOT fall back to `terminal_id`, cwd, ambient shell env, or another server target when the persisted contract is invalid or stale.

#### Scenario: Explicit attach resolves through managed-agent identity
- **WHEN** a developer runs `houmao-mgr agents gateway attach <agent-ref>` for a pair-managed `houmao_server_rest` session
- **THEN** the command resolves `<agent-ref>` through the managed-agent alias set
- **AND THEN** the attach request is issued through the Houmao managed-agent gateway lifecycle surface

#### Scenario: Current-session attach infers the target from tmux session env
- **WHEN** a developer runs `houmao-mgr agents gateway attach` from inside a pair-managed agent tmux session
- **THEN** the command infers the target session from the current tmux session plus stable gateway attachability env pointers
- **AND THEN** the command does not require an explicit agent identity

#### Scenario: Current-session attach uses the persisted server authority and session alias
- **WHEN** a developer runs `houmao-mgr agents gateway attach` from inside a pair-managed agent tmux session
- **AND WHEN** the stable attach contract for that session persists `api_base_url=<server>` and `backend_metadata.session_name=<session-name>`
- **THEN** the command issues the managed-agent gateway attach request against `<server>` with `<session-name>` as `{agent_ref}`
- **AND THEN** it does not retarget the request through `terminal_id` or another alias

#### Scenario: Current-session attach fails closed without Houmao gateway env
- **WHEN** a developer runs `houmao-mgr agents gateway attach` from a tmux session that does not publish the stable Houmao gateway attachability env pointers
- **THEN** the command fails explicitly
- **AND THEN** it does not guess from cwd, ambient shell env, or raw CAO state

#### Scenario: Current-session attach fails closed when the persisted authority no longer resolves
- **WHEN** a developer runs `houmao-mgr agents gateway attach` from inside a pair-managed tmux session
- **AND WHEN** the stable attach contract points at a persisted `api_base_url` plus `session_name` that no longer resolves exactly one managed agent on that server
- **THEN** the command fails explicitly as invalid or stale current-session metadata
- **AND THEN** it does not fall back to `terminal_id` or another server target
