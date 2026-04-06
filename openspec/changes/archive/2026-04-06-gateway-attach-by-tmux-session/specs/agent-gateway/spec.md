## ADDED Requirements

### Requirement: Gateway attach supports explicit tmux-session targeting outside the owning session
For gateway-capable tmux-backed managed sessions, `houmao-mgr agents gateway attach` SHALL support an explicit outside-tmux selector `--target-tmux-session <tmux-session-name>`.

When resolving that selector, the attach flow SHALL treat the addressed tmux session as local-host authority, SHALL prefer `HOUMAO_MANIFEST_PATH` published by that tmux session when present and valid, and SHALL otherwise use exactly one fresh shared-registry record whose `terminal.session_name` matches the selector to recover `runtime.manifest_path`.

After resolution, the attach flow SHALL validate that the resolved manifest still belongs to the addressed tmux session before starting or reusing a gateway.

For pair-managed `houmao_server_rest` sessions, tmux-session targeting SHALL remain a local CLI resolution feature. After local resolution, the attach flow SHALL use the manifest-derived managed-agent pair authority rather than requiring the pair API to accept tmux session names as remote identifiers.

#### Scenario: Outside-tmux attach resolves authority from the addressed tmux session manifest
- **WHEN** an operator runs `houmao-mgr agents gateway attach --target-tmux-session HOUMAO-gpu-coder-1-1775467167530`
- **AND WHEN** that tmux session exists on the local host and publishes a valid `HOUMAO_MANIFEST_PATH`
- **THEN** the attach flow resolves gateway authority from that manifest
- **AND THEN** it validates that the resolved manifest belongs to `HOUMAO-gpu-coder-1-1775467167530` before attaching

#### Scenario: Outside-tmux attach falls back to shared-registry tmux alias recovery
- **WHEN** an operator runs `houmao-mgr agents gateway attach --target-tmux-session HOUMAO-gpu-coder-1-1775467167530`
- **AND WHEN** that tmux session exists on the local host
- **AND WHEN** the tmux-published manifest pointer is missing, blank, or stale
- **AND WHEN** exactly one fresh shared-registry record has `terminal.session_name = "HOUMAO-gpu-coder-1-1775467167530"`
- **THEN** the attach flow recovers `runtime.manifest_path` from that record
- **AND THEN** it still validates the recovered manifest against the addressed tmux session before attaching

#### Scenario: Pair-managed attach uses manifest-derived pair authority after tmux-session resolution
- **WHEN** an operator runs `houmao-mgr agents gateway attach --target-tmux-session HOUMAO-research-1`
- **AND WHEN** the resolved manifest authority identifies a pair-managed `houmao_server_rest` session
- **THEN** the attach flow uses the manifest-derived pair authority for the managed-agent attach request
- **AND THEN** it does not require the pair-managed API to accept `HOUMAO-research-1` as a remote managed-agent identifier
