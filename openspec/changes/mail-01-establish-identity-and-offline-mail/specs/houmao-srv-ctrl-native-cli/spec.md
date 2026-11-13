# Spec Delta

## MODIFIED Requirements

### Requirement: `houmao-mgr agents mail` exposes pair-native mailbox follow-up commands
`houmao-mgr` SHALL expose scoped `agents single ... mail ...` and `agents self mail ...` commands for mailbox discovery and follow-up on managed agents.

At minimum, that family SHALL include:

- `resolve-live`
- `status`
- `list`
- `peek`
- `read`
- `send`
- `post`
- `reply`
- `mark`
- `move`
- `archive`

Those commands SHALL address managed agents by managed-agent reference and SHALL dispatch mailbox work by the resolved managed-agent authority:

- pair-managed targets SHALL use pair-owned mail authority,
- local managed targets SHALL use verified manager-owned local mail authority or verified gateway-backed authority when available,
- when a local live-TUI target lacks verified direct or gateway authority for ordinary mailbox actions such as `list`, `send`, `reply`, or `archive`, the command MAY fall back to TUI-mediated submission and SHALL preserve a non-authoritative submission result instead of claiming mailbox success,
- operator-origin `post` SHALL NOT fall back to TUI-mediated submission and SHALL fail explicitly when verified manager-owned, pair-owned, or gateway-backed authority is unavailable,
- callers SHALL NOT be required to discover or call gateway endpoints directly themselves when using the CLI.

The `agents single` scope SHALL require an explicit `--agent-id` or `--agent-name` before the mail command and SHALL preserve that target even inside another managed session. The `agents self` scope SHALL resolve the current managed agent through manifest-first discovery using `HOUMAO_MANIFEST_PATH` with `HOUMAO_AGENT_ID` as fallback. Outside a resolvable owning session, `agents self` SHALL fail rather than guessing from cwd or ambient shell state.

`resolve-live` SHALL return machine-readable mailbox binding and live gateway discovery data for the resolved managed agent.

For local managed targets, ordinary mailbox follow-up SHALL NOT require prompting the target agent to interpret mailbox instructions when verified manager-owned or gateway-backed mailbox execution is available.

The maintained `agents single` and `agents self` scoped trees SHALL provide these operations. Mail lifecycle operations and notifier controls SHALL require `--channel offline|online`; only summary `mail status` and `resolve-live` SHALL return both channels without selecting one. Missing channel input SHALL fail rather than using canonical mail precedence.

#### Scenario: Same-session resolve-live succeeds without explicit selectors
- **WHEN** an operator or projected skill runs `houmao-mgr agents self mail resolve-live` inside the owning managed tmux session
- **AND WHEN** that tmux session publishes valid manifest-first discovery metadata
- **THEN** `houmao-mgr` resolves the current managed agent through that tmux-local discovery contract
- **AND THEN** the command returns the current mailbox binding and any live gateway discovery data without requiring `--agent-id` or `--agent-name`

#### Scenario: Explicit selector wins over same-session discovery
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice mail status` from inside a different managed tmux session
- **THEN** `houmao-mgr` targets the explicitly selected managed agent
- **AND THEN** the command does not silently replace that explicit target with the caller's current session

#### Scenario: Outside-tmux mail discovery fails without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents self mail resolve-live` outside tmux
- **AND WHEN** the command is not given `--agent-id` or `--agent-name`
- **THEN** the command fails explicitly
- **AND THEN** it does not guess a managed-agent target from cwd, gateway listener bindings, or ambient shell state

#### Scenario: Local mail list uses manager-owned direct mailbox execution
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice mail list --channel offline`
- **AND WHEN** `alice` resolves to local managed-agent authority on the current host
- **THEN** `houmao-mgr` performs mailbox follow-up through manager-owned local mail authority
- **AND THEN** the command does not require prompting the target agent to interpret mailbox instructions for that ordinary mailbox list

#### Scenario: Local live-TUI send without verified direct authority returns submission-only fallback
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice mail send --channel offline --to bob@houmao.localhost --subject "..." --body-content "..."`
- **AND WHEN** `alice` resolves to a local live-TUI managed-agent target
- **AND WHEN** verified manager-owned or gateway-backed mail execution is unavailable for that action
- **THEN** `houmao-mgr` returns a non-authoritative submission result for that mailbox request
- **AND THEN** the command does not claim verified mailbox success solely from TUI transcript recovery

#### Scenario: Local live-TUI post without verified authority fails explicitly
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice mail post --channel offline --subject "..." --body-content "..."`
- **AND WHEN** `alice` resolves to a local live-TUI managed-agent target
- **AND WHEN** verified manager-owned or gateway-backed mail execution is unavailable for that action
- **THEN** the command fails explicitly instead of returning a submission-only mailbox result
- **AND THEN** it does not ask the target agent to impersonate `HOUMAO-operator@houmao.localhost`

#### Scenario: Pair-managed target still uses pair-owned mail authority
- **WHEN** an operator runs `houmao-mgr agents single --agent-id abc123 mail post --channel offline --subject "..." --body-content "..."`
- **AND WHEN** `abc123` resolves through pair authority
- **THEN** `houmao-mgr` dispatches that mailbox action through the supported pair-owned mail authority
- **AND THEN** the operator does not need to discover or address the pair-owned gateway endpoint directly

### Requirement: `houmao-mgr agents mail` exposes mailbox lifecycle commands
`houmao-mgr agents single ... mail` SHALL expose a mailbox lifecycle command family for managed-agent mailbox work.

At minimum, that family SHALL include:

- `resolve-live`,
- `status`,
- `list`,
- `peek`,
- `read`,
- `send`,
- `post`,
- `reply`,
- `mark`,
- `move`,
- `archive`.

`list` SHALL support selecting a mailbox box and SHALL default to the inbox when omitted.

`peek` SHALL retrieve one message without marking it read.

`read` SHALL retrieve one message and mark it read.

`reply` SHALL mark the replied message answered after a successful reply.

`mark` SHALL allow explicit manual marking of supported lifecycle fields such as `read` and `answered`.

`move` SHALL move selected messages among supported mailbox boxes.

`archive` SHALL archive selected messages and remain a shortcut for the common processed-mail completion operation.

The CLI SHALL keep the existing authority-aware result contract for verified execution versus non-authoritative fallback submission.

The maintained `agents single` and `agents self` scoped trees SHALL provide these operations. Mail lifecycle operations and notifier controls SHALL require `--channel offline|online`; only summary `mail status` and `resolve-live` SHALL return both channels without selecting one. Missing channel input SHALL fail rather than using canonical mail precedence.

#### Scenario: Operator archives selected mail from the CLI
- **WHEN** an operator runs `houmao-mgr agents single ... mail archive` with one or more message refs
- **THEN** the command resolves the target mailbox binding through the supported managed-agent selector contract
- **AND THEN** it archives the selected messages through the live gateway or manager-owned fallback surface

#### Scenario: CLI peek does not mark a message read
- **WHEN** an operator runs `houmao-mgr agents single ... mail peek --message-ref <ref>`
- **THEN** the command returns the selected message content
- **AND THEN** the selected message is not marked read merely because of that peek operation

#### Scenario: CLI read marks a message read
- **WHEN** an operator runs `houmao-mgr agents single ... mail read --message-ref <ref>`
- **THEN** the command returns the selected message content
- **AND THEN** the selected message is marked read for the target mailbox principal

### Requirement: Native gateway mail-notifier CLI configures notification mode
`houmao-mgr agents single ... gateway mail-notifier enable` SHALL accept an optional notifier mode argument with values `any_inbox` and `unread_only`.

When the operator omits the notifier mode, the command SHALL send the gateway notifier enable request with effective mode `any_inbox`.

When the operator supplies `unread_only`, the command SHALL send the gateway notifier enable request with mode `unread_only`.

`houmao-mgr agents single ... gateway mail-notifier enable` SHALL also accept an optional `--appendix-text` argument that updates notifier `appendix_text`.

When the operator omits `--appendix-text`, the CLI SHALL send the notifier enable request without an appendix field so the gateway can preserve the stored appendix unchanged.

When the operator supplies non-empty `--appendix-text`, the CLI SHALL send that exact string as notifier `appendix_text`.

When the operator supplies `--appendix-text ""`, the CLI SHALL send `appendix_text=""` so the gateway clears the stored appendix.

The command output for notifier status and enable results SHALL preserve both the `mode` field and the effective `appendix_text` returned by the gateway.

The maintained `agents single` and `agents self` scoped trees SHALL provide these operations. Mail lifecycle operations and notifier controls SHALL require `--channel offline|online`; only summary `mail status` and `resolve-live` SHALL return both channels without selecting one. Missing channel input SHALL fail rather than using canonical mail precedence.

#### Scenario: CLI enable defaults to any-inbox mode
- **WHEN** an operator runs `houmao-mgr agents single --agent-id abc123 gateway mail-notifier enable --channel offline --interval-seconds 60` without a mode option
- **THEN** the CLI sends a notifier enable request with mode `any_inbox`
- **AND THEN** the emitted result includes the gateway-reported `mode`

#### Scenario: CLI enable accepts unread-only mode
- **WHEN** an operator runs `houmao-mgr agents single --agent-id abc123 gateway mail-notifier enable --channel offline --interval-seconds 60 --mode unread_only`
- **THEN** the CLI sends a notifier enable request with mode `unread_only`
- **AND THEN** it does not require the operator to address the raw `/v1/mail-notifier` route directly

#### Scenario: CLI rejects invalid notifier mode
- **WHEN** an operator runs `houmao-mgr agents single ... gateway mail-notifier enable --interval-seconds 60 --mode read`
- **THEN** the CLI rejects the invocation as invalid input
- **AND THEN** it does not send a notifier enable request with an unknown mode value

#### Scenario: CLI omits appendix field when not provided
- **WHEN** an operator runs `houmao-mgr agents single --agent-id abc123 gateway mail-notifier enable --channel offline --interval-seconds 60` without `--appendix-text`
- **THEN** the CLI sends the notifier enable request without an appendix field
- **AND THEN** the gateway can preserve previously stored appendix text unchanged

#### Scenario: CLI forwards non-empty appendix text
- **WHEN** an operator runs `houmao-mgr agents single --agent-id abc123 gateway mail-notifier enable --channel offline --interval-seconds 60 --appendix-text "Watch for high-priority mailbox work first."`
- **THEN** the CLI sends that exact string as notifier `appendix_text`
- **AND THEN** the emitted result includes the gateway-reported effective appendix text

#### Scenario: CLI forwards empty appendix text to clear appendix
- **WHEN** an operator runs `houmao-mgr agents single --agent-id abc123 gateway mail-notifier enable --channel offline --interval-seconds 60 --appendix-text ""`
- **THEN** the CLI sends `appendix_text=""` to the gateway
- **AND THEN** it does not reinterpret the empty string as omitted input

### Requirement: `houmao-mgr agents mailbox` exposes local late mailbox registration commands
The maintained `agents single` and `agents self` scopes SHALL expose `mailbox offline status|join|leave` for an existing locally controlled body. Join SHALL select a configured local registry or explicit authorized remote registry connection. The command SHALL not require body relaunch, grant remote lifecycle authority, or provide force/stash address takeover. Explicit leave SHALL preserve the online binding.

#### Scenario: Operator inspects late registration commands
- **WHEN** an operator opens scoped `mailbox offline --help`
- **THEN** help lists status, join, and leave with local/remote registry selection
- **AND THEN** it does not advertise register/unregister compatibility aliases or force/stash takeover

#### Scenario: Remote registry join keeps the body running
- **WHEN** an existing locally controlled agent joins an authorized remote registry
- **THEN** the CLI reports the confirmed offline registration without replacing the body or its online binding

#### Scenario: Operator uses a native late mailbox registration path under `agents`
- **WHEN** an operator runs `houmao-mgr agents single --agent-id abc123 mailbox offline join` against a configured registry
- **THEN** the command uses the supported runtime and registry services
- **AND THEN** it does not require a raw module entrypoint or body restart

## ADDED Requirements

### Requirement: Native agent creation exposes explicit identity generation modes
Creation-facing commands SHALL default `--agent-id-mode` to `uuid` and allow explicit `name-hash`. A supplied `--agent-id` SHALL select that identity; combining it with an explicitly supplied generation mode SHALL fail. Existing-agent commands SHALL use the persisted identity and SHALL not offer generation as a repair for missing durable identity.

#### Scenario: Default creation names do not determine IDs
- **WHEN** an operator creates two new agents with the same friendly name and no ID override
- **THEN** the results contain separately generated UUIDs

#### Scenario: Caller requests name-hash mode
- **WHEN** creation explicitly selects `--agent-id-mode name-hash`
- **THEN** it uses the normalized-name derivation and reports the chosen ID
- **AND THEN** the caller remains responsible for name uniqueness

#### Scenario: Conflicting ID inputs fail before creation
- **WHEN** a caller supplies both an explicit ID and explicit generation mode
- **THEN** the command fails before agent or registry publication
