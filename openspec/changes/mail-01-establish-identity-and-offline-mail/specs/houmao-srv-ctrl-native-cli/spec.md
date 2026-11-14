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
- **WHEN** an operator runs `houmao-mgr agents single ... mail archive --channel offline` with one or more message refs
- **THEN** the command resolves the target mailbox binding through the supported managed-agent selector contract
- **AND THEN** it archives the selected messages through the live gateway or manager-owned fallback surface

#### Scenario: CLI peek does not mark a message read
- **WHEN** an operator runs `houmao-mgr agents single ... mail peek --channel offline --message-ref <ref>`
- **THEN** the command returns the selected message content
- **AND THEN** the selected message is not marked read merely because of that peek operation

#### Scenario: CLI read marks a message read
- **WHEN** an operator runs `houmao-mgr agents single ... mail read --channel offline --message-ref <ref>`
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
- **AND THEN** it does not require the operator to address the raw `/v1/mail-notifier/{channel}` route directly

#### Scenario: CLI rejects invalid notifier mode
- **WHEN** an operator runs `houmao-mgr agents single ... gateway mail-notifier enable --channel offline --interval-seconds 60 --mode read`
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

### Requirement: `houmao-mgr` renders expected mailbox-related operator failures without Python tracebacks
When a native `houmao-mgr` mailbox-management or gateway mail-notifier command hits an expected operator-facing failure, the CLI SHALL render that failure as explicit command-line error output rather than leaking a Python traceback from the top-level wrapper.

This SHALL apply at minimum to:

- `houmao-mgr agents single ... mailbox offline join`
- `houmao-mgr agents single ... mailbox offline leave`
- `houmao-mgr agents single ... mailbox offline status`
- `houmao-mgr agents self mail ...`
- `houmao-mgr agents single ... gateway mail-notifier status`
- `houmao-mgr agents single ... gateway mail-notifier enable`
- `houmao-mgr agents single ... gateway mail-notifier disable`

The wrapper SHALL preserve the command's non-zero exit behavior for those failures.
This requirement covers expected operator-facing failures such as explicit Click-style usage errors, manifest/runtime readiness errors, and gateway readiness errors that the command path already classifies as normal command failures.
The CLI SHALL NOT claim success or hide the failure reason; it SHALL surface the explicit operator-facing error text without the Python stack trace.

#### Scenario: Joined mailbox registration failure renders as a clean CLI error
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice mailbox offline join --mailbox-root /tmp/shared-mail`
- **AND WHEN** the command fails with an expected operator-facing mailbox-registration error
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports the failure as clean CLI error text without a Python traceback

#### Scenario: Gateway mail-notifier enable failure renders as a clean CLI error
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice gateway mail-notifier enable --channel offline --interval-seconds 60`
- **AND WHEN** the command fails with an expected operator-facing gateway notifier readiness error
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports the failure as clean CLI error text without a Python traceback

### Requirement: Server-backed gateway raw control and notifier commands accept passive server pair authorities
`houmao-mgr` server-backed `agents gateway send-keys` and `agents single ... gateway mail-notifier ...` command paths SHALL accept `houmao-passive-server` as a supported pair authority whenever those commands operate through an explicit pair authority instead of a resumed local controller.

For these commands, `houmao-mgr` SHALL resolve the pair client through the supported pair-authority factory and SHALL use the passive server's managed-agent gateway proxy routes rather than requiring direct listener discovery from the caller.

#### Scenario: Gateway raw control input works through a passive server
- **WHEN** an operator runs `houmao-mgr agents gateway send-keys --agent-id abc123 --port 9891 --sequence "<[Escape]>"`
- **AND WHEN** the addressed pair authority identifies `houmao-passive-server`
- **THEN** `houmao-mgr` sends that raw control-input request through the passive server's managed-agent gateway proxy route
- **AND THEN** the command does not fail only because the selected pair authority is passive

#### Scenario: Gateway mail notifier control works through a passive server
- **WHEN** an operator runs `houmao-mgr agents single --agent-id abc123 gateway mail-notifier status --channel offline --port 9891`
- **AND WHEN** the addressed pair authority identifies `houmao-passive-server`
- **THEN** `houmao-mgr` reads notifier status through the passive server's managed-agent gateway proxy route
- **AND THEN** the command does not require the operator to contact the gateway listener endpoint directly

### Requirement: `houmao-mgr mailbox messages` reports structural mailbox message inspection

The native `houmao-mgr mailbox messages list` and `houmao-mgr mailbox messages get` commands SHALL act as structural inspection over one filesystem mailbox root and one selected mailbox address.

Those commands MAY return canonical message metadata and address-scoped projection metadata for the selected address, including message identity, thread identity, projection folder, projection path, canonical path, sender metadata, recipient metadata, body content, headers, and attachments.

Those commands SHALL NOT report participant-local mutable mailbox view-state fields such as `read`, `starred`, `archived`, or `deleted`.

When an operator needs participant-local read or unread follow-up state, the supported surface SHALL be actor-scoped mail commands such as `houmao-mgr agents self mail ...` or a future explicitly address-scoped state surface rather than mailbox-root administration commands.

#### Scenario: Root mailbox message list omits participant-local view-state flags

- **WHEN** an operator runs `houmao-mgr mailbox messages list --mailbox-root /tmp/shared-mail --address alice@agents.localhost`
- **THEN** the command returns structural message summaries for the selected address projection
- **AND THEN** each message summary may include fields such as `message_id`, `thread_id`, `subject`, `sender_address`, `folder`, `projection_path`, and `canonical_path`
- **AND THEN** the payload does not include `read`, `starred`, `archived`, or `deleted`

#### Scenario: Root mailbox message get omits participant-local view-state flags

- **WHEN** an operator runs `houmao-mgr mailbox messages get --mailbox-root /tmp/shared-mail --address alice@agents.localhost --message-id msg-123`
- **THEN** the command returns canonical message details together with the selected address projection metadata
- **AND THEN** the payload may include sender, recipients, headers, body content, attachments, `folder`, and `projection_path`
- **AND THEN** the payload does not claim a single authoritative participant-local read, starred, archived, or deleted state

### Requirement: `houmao-mgr agents mail post` defaults to operator mailbox replies
`houmao-mgr agents single ... mail post` SHALL default omitted `--reply-policy` input to `operator_mailbox`.

The command SHALL continue to accept explicit `--reply-policy none` and explicit `--reply-policy operator_mailbox`.

When `--reply-policy none` is supplied, the created operator-origin message SHALL remain no-reply and later replies against that message SHALL fail explicitly.

When `--reply-policy` is omitted or supplied as `operator_mailbox`, the created operator-origin message SHALL allow replies back to the reserved operator mailbox `HOUMAO-operator@houmao.localhost`.

The command help SHALL report the reply-policy default as `operator_mailbox`.

#### Scenario: Omitted CLI reply policy creates a reply-enabled operator-origin post
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice mail post --channel offline --subject "..." --body-content "..."` without `--reply-policy`
- **THEN** `houmao-mgr` dispatches the post with reply policy `operator_mailbox`
- **AND THEN** the resulting operator-origin message accepts replies to `HOUMAO-operator@houmao.localhost`

#### Scenario: Explicit CLI no-reply policy remains supported
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice mail post --channel offline --subject "..." --body-content "..." --reply-policy none`
- **THEN** `houmao-mgr` dispatches the post with reply policy `none`
- **AND THEN** a later reply against that operator-origin message is rejected explicitly

#### Scenario: CLI help reflects the new default
- **WHEN** an operator reads help for `houmao-mgr agents single ... mail post`
- **THEN** the `--reply-policy` option reports `operator_mailbox` as the default
- **AND THEN** it still lists `none` as the no-reply opt-out value

### Requirement: `houmao-mgr agents mail send` and `post` accept `--notify-block` and respect the houmao-notify body fence
`houmao-mgr agents single ... mail send` and `houmao-mgr agents single ... mail post` SHALL accept an optional `--notify-block <text>` flag whose value populates the canonical envelope's `notify_block.text` field through the supported composition path.

The two commands SHALL also accept an optional `--notify-block-placement [append|prepend]` flag whose value populates `notify_block.placement`. The flag SHALL default to `append`. When `--notify-block` is omitted, `--notify-block-placement` SHALL be ignored and SHALL NOT influence body-fence extraction.

When `--notify-block` is provided, the CLI SHALL submit the canonical envelope's typed `notify_block` shape with the supplied `text` and `placement` through the supported composition contract. The CLI SHALL NOT also re-extract `notify_block` from a `houmao-notify` body fence on top of the explicit value. Composition SHALL apply the canonical auto-mirror invariant (synthesize a `houmao-notify` fenced block in `body_markdown` at the requested `placement` when one is not already present).

When `--notify-block` is omitted and `--body-content` (or the equivalent body-source flag) contains a Markdown fenced code block with info-string `houmao-notify`, the CLI SHALL submit the body source unchanged through the canonical composition contract so the protocol-side extractor populates `notify_block.text` from the first matching fence per the canonical rules and defaults `notify_block.placement` to `"append"`.

The CLI SHALL surface the canonical 512-character truncation outcome and the canonical "verifier not yet supported" rejection as explicit command-line errors, not as Python tracebacks.

The CLI SHALL NOT introduce a separate `--notify-auth-*` family of flags in this change. Callers requiring `notify_auth` metadata SHALL set it through programmatic composition surfaces; the CLI SHALL accept an absent `notify_auth` (treated as no authentication metadata) for normal `send` and `post` invocations.

#### Scenario: Operator supplies an explicit notify-block on send with default placement
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice mail send --channel offline --to bob@houmao.localhost --subject "..." --body-content "..." --notify-block "re-run on official path"`
- **AND WHEN** the resolved managed-agent authority supports verified mail execution for that send
- **THEN** the canonical mail message stores `notify_block.text="re-run on official path"` and `notify_block.placement="append"`
- **AND THEN** the persisted `body_markdown` contains a `houmao-notify` fenced block matching that text appended after the supplied body content

#### Scenario: Operator supplies notify-block with prepend placement on post
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice mail post --channel offline --subject "..." --body-content "Operator note." --notify-block "OPERATOR DIRECTIVE" --notify-block-placement prepend`
- **AND WHEN** the resolved managed-agent authority supports verified operator-origin mail execution for that post
- **THEN** the canonical mail message stores `notify_block.text="OPERATOR DIRECTIVE"` and `notify_block.placement="prepend"`
- **AND THEN** the persisted `body_markdown` begins with a `houmao-notify` fenced block matching that text, followed by the supplied body content

#### Scenario: Operator authors notify content via body fence on post
- **WHEN** an operator runs `houmao-mgr agents single --agent-name alice mail post --channel offline --subject "..." --body-content $'hello\n\n` ` ` `houmao-notify\ncontinue current task\n` ` ` `'`
- **AND WHEN** the operator does not pass `--notify-block`
- **AND WHEN** the resolved managed-agent authority supports verified operator-origin mail execution for that post
- **THEN** the canonical mail message stores `notify_block.text="continue current task"` and `notify_block.placement="append"`
- **AND THEN** the persisted `body_markdown` still contains the original fenced block

#### Scenario: Oversize notify-block surfaces a clean CLI error rather than a traceback
- **WHEN** an operator runs `houmao-mgr agents single ... mail send` with `--notify-block` content longer than 512 characters
- **THEN** the canonical composition truncates per the protocol rule and the CLI reports the truncation outcome through explicit command-line output
- **AND THEN** the CLI does not leak a Python traceback from the top-level wrapper

#### Scenario: Unsupported notify-auth scheme surfaces a clean CLI error
- **WHEN** a programmatic composition path attached to a scoped `agents single` or `agents self` mail invocation supplies a `notify_auth.scheme` other than `none`
- **THEN** the CLI surfaces the canonical "verifier not yet supported" rejection as an explicit command-line error
- **AND THEN** the CLI does not leak a Python traceback from the top-level wrapper

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
