## Purpose
Define the Houmao-owned native `houmao-mgr` command tree for covered pair workflows, including server-backed managed-agent operations and local utility commands.
## Requirements
### Requirement: `houmao-mgr` exposes a native pair-operations command tree
`houmao-mgr` SHALL expose a Houmao-owned top-level native command tree.

At minimum, that native tree SHALL include:

- `server`
- `agents`
- `brains`
- `credentials`
- `admin`
- `mailbox`
- `project`
- `system-skills`

Those command families SHALL be documented as Houmao-owned pair commands or Houmao-owned local operator commands, as appropriate.

The root group SHALL use `invoke_without_command=True` so that running `houmao-mgr` without arguments prints help text instead of raising a Python exception.

The root group SHALL accept `--print-plain`, `--print-json`, and `--print-fancy` as mutually exclusive flag-value options that control the output formatting style for all subcommands. The resolved print style SHALL be stored in `click.Context.obj["output"]` as an `OutputContext` instance accessible to all subcommands.

The root group SHALL also accept `--version` as a root-level version-reporting option. When invoked, `houmao-mgr --version` SHALL print the packaged Houmao version and exit successfully without requiring a subcommand.

The root help surface SHALL point readers to the published detailed Houmao documentation at `https://igamenovoer.github.io/houmao/`.

Top-level `launch` and the explicit `cao` namespace SHALL NOT remain part of the supported command tree.

#### Scenario: Native help surface shows the new top-level command families
- **WHEN** an operator runs `houmao-mgr --help`
- **THEN** the help output includes `server`, `agents`, `brains`, `credentials`, `admin`, `mailbox`, `project`, and `system-skills`
- **AND THEN** the help output does NOT include `cao` or top-level `launch`

#### Scenario: Bare invocation prints help instead of raising an exception
- **WHEN** an operator runs `houmao-mgr` without any arguments
- **THEN** the CLI prints help text showing available command groups
- **AND THEN** the CLI does NOT raise a Python exception or print a stack trace

#### Scenario: Root group help shows print style flags
- **WHEN** an operator runs `houmao-mgr --help`
- **THEN** the help output lists `--print-plain`, `--print-json`, and `--print-fancy` as available options

#### Scenario: Root group help shows the version flag
- **WHEN** an operator runs `houmao-mgr --help`
- **THEN** the help output lists `--version` as an available root option

#### Scenario: Root version request prints the packaged Houmao version
- **WHEN** an operator runs `houmao-mgr --version`
- **THEN** the CLI prints the packaged Houmao version
- **AND THEN** the command exits successfully without requiring a subcommand

#### Scenario: Root help points readers to the detailed docs site
- **WHEN** an operator runs `houmao-mgr --help`
- **THEN** the help output includes `https://igamenovoer.github.io/houmao/`
- **AND THEN** the wording makes clear that the link is for more detailed documentation

#### Scenario: Bare invocation also exposes the detailed docs link
- **WHEN** an operator runs `houmao-mgr` without arguments
- **THEN** the printed help output includes `https://igamenovoer.github.io/houmao/`
- **AND THEN** the operator can discover the published docs site without already knowing a subcommand


### Requirement: `houmao-mgr` exposes `credentials` as a top-level native command family
`houmao-mgr` SHALL expose `credentials` as a top-level native command family in the supported root command tree.

The root help surface SHALL present `credentials` as the first-class Houmao-owned credential-management family rather than as a nested projection-maintenance detail.

#### Scenario: Native help surface shows the credentials command family
- **WHEN** an operator runs `houmao-mgr --help`
- **THEN** the help output includes `credentials` among the supported top-level command families
- **AND THEN** the help output presents `credentials` as the supported credential-management surface

### Requirement: `houmao-mgr project` exposes repo-local project views
When `houmao-mgr` exposes the repo-local `project` command family, that family SHALL include:

- `init`
- `status`
- `agents`
- `easy`
- `credentials`
- `mailbox`

The `project` help surface SHALL present those subtrees as repo-local views over project source management, high-level project authoring, project-scoped credential management, and project-scoped mailbox operations.

#### Scenario: Project help shows the project views
- **WHEN** an operator runs `houmao-mgr project --help`
- **THEN** the help output lists `init`, `status`, `agents`, `easy`, `credentials`, and `mailbox`
- **AND THEN** the help output does not present `agent-tools` as the supported public project command family

### Requirement: `houmao-mgr server` accepts passive server pair authorities
`houmao-mgr server` lifecycle commands SHALL accept a supported pair authority whose `GET /health` reports `houmao_service == "houmao-passive-server"` in addition to `houmao-server`.

At minimum, this SHALL apply to status-style inspection and shutdown-style control commands that operate through the pair authority.

#### Scenario: Server status works against a passive server
- **WHEN** an operator runs `houmao-mgr server status --port 9891`
- **AND WHEN** the addressed server's `GET /health` response identifies `houmao-passive-server`
- **THEN** `houmao-mgr` returns lifecycle status instead of rejecting the server as unsupported

#### Scenario: Server stop works against a passive server
- **WHEN** an operator runs `houmao-mgr server stop --port 9891`
- **AND WHEN** the addressed server's `GET /health` response identifies `houmao-passive-server`
- **THEN** `houmao-mgr` calls the passive-server shutdown contract successfully
- **AND THEN** the command does not require the operator to switch back to the old server CLI

### Requirement: `houmao-mgr agents` is the preferred pair-native managed-agent command family
`houmao-mgr agents ...` SHALL be the preferred pair-native command family for managed-agent operations.

At minimum, the `agents` family SHALL include commands for:

- `launch`
- `join`
- `list`
- `state`
- `prompt`
- `interrupt`
- `relaunch`
- `stop`

Those commands SHALL target managed-agent identities rather than raw `terminal_id` or raw CAO session names as their normative addressing model.
Within that family, `join` SHALL adopt an existing tmux-backed agent session into managed-agent control without requiring `houmao-server` or raw tmux attach scripts.
Within that family, `state` SHALL present the operational summary view for supported managed-agent inspection.
The native `agents` family SHALL NOT advertise or require a detail-oriented `show` command or a generic `history` command as part of its supported managed-agent inspection contract.

#### Scenario: Operator inspects managed-agent state through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed-agent identity through registry-first discovery or the supported pair authority
- **AND THEN** the command returns the managed-agent state without requiring the operator to switch to raw CAO session or terminal identities

#### Scenario: Operator joins an existing tmux-backed session through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents join --agent-name coder` from a compatible tmux session
- **THEN** `houmao-mgr` adopts the existing tmux-backed session into managed-agent control through the native pair CLI
- **AND THEN** later `houmao-mgr agents state --agent-name coder` can resolve that managed agent without requiring raw tmux session names or manual manifest-path discovery

#### Scenario: Operator submits a prompt through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id abc123 --prompt "..." `
- **THEN** `houmao-mgr` submits that request through registry-first discovery or the pair-managed agent control authority
- **AND THEN** the command does not require the operator to know whether the agent is server-backed or locally-backed

#### Scenario: Operator relaunches a managed tmux-backed session through the native `agents` tree
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed-agent identity through registry-first discovery or tmux-local current-session authority
- **AND THEN** the command relaunches the existing tmux-backed managed session rather than constructing a new launch

#### Scenario: Help output does not advertise retired inspection commands
- **WHEN** an operator runs `houmao-mgr agents --help`
- **THEN** the help output does not list `show` or `history`
- **AND THEN** supported inspection guidance points operators to `state`, `agents gateway tui ...`, or `agents turn ...` rather than removed managed-agent inspection commands

### Requirement: `houmao-mgr agents gateway` exposes gateway lifecycle and gateway-mediated request commands
`houmao-mgr` SHALL expose a native `agents gateway ...` command family for managed-agent gateway operations.

At minimum, that family SHALL include:

- `attach`
- `detach`
- `status`
- `prompt`
- `interrupt`
- `send-keys`
- `mail-notifier status`
- `mail-notifier enable`
- `mail-notifier disable`

`agents gateway prompt` SHALL target the managed agent's live gateway direct prompt-control path rather than the transport-neutral managed-agent request path or the queued gateway request path.
`agents gateway interrupt` SHALL continue targeting the managed agent's live gateway-mediated interrupt path.
`agents gateway send-keys` SHALL target the managed agent's dedicated live gateway raw control-input path rather than the queued gateway request path, and it SHALL NOT apply prompt-readiness or busy gating before forwarding that raw input.
`agents gateway mail-notifier ...` SHALL target the managed agent's live gateway mail-notifier control path rather than the foreground managed-agent mail follow-up path.
The documented default prompt path for ordinary pair-native prompt submission SHALL remain `houmao-mgr agents prompt ...`. `agents gateway prompt` SHALL be documented as the explicit live gateway prompt-control path for operators who want ready-or-refuse behavior and optional `--force` override semantics.

#### Scenario: Operator attaches a gateway through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway attach --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed agent through the supported authority for that target
- **AND THEN** the command attaches or reuses the live gateway for that managed agent

#### Scenario: Operator submits a gateway-controlled prompt through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway prompt --agent-id abc123 --prompt "..."`
- **THEN** `houmao-mgr` delivers that request through the managed agent's live gateway direct prompt-control path
- **AND THEN** the command does not require the operator to discover or address the gateway listener endpoint directly

#### Scenario: Operator submits raw control input through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway send-keys --agent-id abc123 --sequence "/model<[Enter]>"`
- **THEN** `houmao-mgr` delivers that request through the managed agent's dedicated live gateway raw control-input path
- **AND THEN** the command does not reinterpret that raw control input as a queued semantic prompt request

#### Scenario: Operator enables mail notifier through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier enable --agent-id abc123 --interval-seconds 60`
- **THEN** `houmao-mgr` delivers that request through the managed agent's live gateway mail-notifier control path
- **AND THEN** the command does not require the operator to discover or address the gateway listener endpoint directly

#### Scenario: Ordinary prompt guidance points operators to the transport-neutral path by default
- **WHEN** repo-owned help text or docs explain how to submit an ordinary prompt through the native pair CLI
- **THEN** they present `houmao-mgr agents prompt ...` as the default documented path
- **AND THEN** they present `houmao-mgr agents gateway prompt ...` as the explicit gateway-managed alternative rather than the default

### Requirement: `houmao-mgr agents gateway reminders` exposes a native reminder command family
`houmao-mgr` SHALL expose a native `agents gateway reminders ...` command family for live gateway reminder operations on managed agents.

At minimum, that family SHALL include:

- `list`
- `get`
- `create`
- `set`
- `remove`

Those commands SHALL operate through managed-agent resolution and live gateway authority rather than requiring operators to address raw gateway listener URLs directly.

`create` SHALL accept exactly one reminder definition per invocation.

`set` SHALL target exactly one existing reminder identified by `--reminder-id`.

#### Scenario: Operator lists reminders through the native gateway tree
- **WHEN** an operator runs `houmao-mgr agents gateway reminders list --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed agent through the supported authority for that target
- **AND THEN** the command returns the live reminder-set view without requiring the operator to know the gateway base URL

#### Scenario: Operator creates one prompt reminder through the native gateway tree
- **WHEN** an operator runs `houmao-mgr agents gateway reminders create --agent-id abc123 --title "Check inbox" --mode one_off --prompt "Review the inbox now." --ranking 0 --start-after-seconds 300`
- **THEN** `houmao-mgr` delivers that request through the managed agent's live gateway reminder control path
- **AND THEN** the command does not require the operator to submit raw `/v1/reminders` HTTP manually

#### Scenario: Operator removes one reminder through the native gateway tree
- **WHEN** an operator runs `houmao-mgr agents gateway reminders remove --agent-id abc123 --reminder-id greminder-123`
- **THEN** `houmao-mgr` deletes that live reminder through the managed agent's gateway reminder control path
- **AND THEN** the command returns a structured success result for that reminder id

### Requirement: `houmao-mgr agents gateway reminders` supports the same targeting contract as the rest of `agents gateway`
Gateway-targeting `houmao-mgr agents gateway reminders ...` commands that operate on one managed agent SHALL support the same managed-agent selector contract as the rest of `agents gateway`.

At minimum, this SHALL apply to:

- `list`
- `get`
- `create`
- `set`
- `remove`

Those commands SHALL accept:

- `--agent-id`
- `--agent-name`
- `--current-session`
- `--target-tmux-session`
- `--pair-port`

with the same mutual-exclusion and current-session rules used by the rest of `agents gateway`.

Server-backed reminder command paths SHALL accept `houmao-passive-server` as a supported pair authority whenever reminder operations are routed through an explicit pair authority instead of a resumed local controller.

#### Scenario: Current-session reminder inspection resolves the owning managed session
- **WHEN** an operator runs `houmao-mgr agents gateway reminders list` from inside the owning managed tmux session
- **THEN** `houmao-mgr` resolves the target through the manifest-first current-session contract used by the rest of `agents gateway`
- **AND THEN** the reminder command does not require an explicit managed-agent selector in that same-session case

#### Scenario: Pair-backed reminder creation works through passive-server authority
- **WHEN** an operator runs `houmao-mgr agents gateway reminders create --agent-id abc123 --pair-port 9891 --title "Check inbox" --mode one_off --prompt "Review the inbox now." --ranking 0 --start-after-seconds 300`
- **AND WHEN** the addressed pair authority reports `houmao_service == "houmao-passive-server"`
- **THEN** `houmao-mgr` routes the reminder create request through the passive-server managed-agent gateway proxy
- **AND THEN** the command does not reject the passive server as unsupported for reminder control

### Requirement: `houmao-mgr agents gateway reminders create` and `set` support numeric ranking plus prepend and append placement modes
The native reminder CLI SHALL keep ranking numeric.

`houmao-mgr agents gateway reminders create` SHALL require exactly one of:

- `--ranking <int>`
- `--before-all`
- `--after-all`

`houmao-mgr agents gateway reminders set` SHALL preserve the existing ranking when no ranking option is supplied, and when ranking change is requested it SHALL accept at most one of those same ranking modes.

The CLI SHALL NOT expose named priority aliases such as `high`, `normal`, or `low`.

`--before-all` SHALL compute the concrete ranking as one less than the smallest current reminder ranking in the live reminder set.

`--after-all` SHALL compute the concrete ranking as one more than the largest current reminder ranking in the live reminder set.

When the live reminder set is empty, both `--before-all` and `--after-all` SHALL resolve to ranking `0`.

`set` SHALL behave as a CLI-side partial update surface: unspecified reminder fields remain unchanged in the effective update even though the gateway reminder API remains full-replacement `PUT`.

#### Scenario: `--before-all` computes a higher-priority numeric ranking
- **WHEN** the live reminder set contains reminders ranked `-20`, `-10`, and `0`
- **AND WHEN** an operator runs `houmao-mgr agents gateway reminders create --agent-id abc123 --title "Urgent follow-up" --mode one_off --prompt "Resume now." --before-all --start-after-seconds 60`
- **THEN** the CLI computes the new reminder ranking as `-21`
- **AND THEN** the created reminder becomes higher priority than the previously smallest-ranked reminder

#### Scenario: `--after-all` resolves to zero on an empty live set
- **WHEN** the live reminder set is empty
- **AND WHEN** an operator runs `houmao-mgr agents gateway reminders create --agent-id abc123 --title "First reminder" --mode one_off --prompt "Start now." --after-all --start-after-seconds 60`
- **THEN** the CLI computes the created reminder ranking as `0`
- **AND THEN** the command succeeds without requiring the operator to guess an initial ranking number

#### Scenario: `set` reranks one reminder without restating unchanged fields
- **WHEN** reminder `greminder-123` already exists with unchanged prompt, title, timing, and delivery kind fields
- **AND WHEN** an operator runs `houmao-mgr agents gateway reminders set --agent-id abc123 --reminder-id greminder-123 --before-all`
- **THEN** the CLI preserves the reminder's unchanged fields while recomputing only the ranking placement
- **AND THEN** the resulting full reminder update sent to the gateway reflects the new ranking and the original unchanged fields

### Requirement: `houmao-mgr agents gateway prompt` returns structured JSON send results and refusal errors

`houmao-mgr agents gateway prompt` SHALL return structured JSON describing prompt dispatch outcome.

On success, the command SHALL print a JSON success payload stating that the prompt was sent.

When the live gateway refuses prompt control because the target is not ready, already busy, unavailable, unsupported, or otherwise cannot accept the prompt, the command SHALL print a structured JSON error payload and SHALL exit non-zero.

The command SHALL accept `--force`, which forwards `force = true` to the live gateway prompt-control route.

#### Scenario: Ready prompt dispatch prints JSON success
- **WHEN** an operator runs `houmao-mgr agents gateway prompt --agent-id abc123 --prompt "..."`
- **AND WHEN** the addressed target is prompt-ready
- **THEN** the command prints structured JSON reporting that the prompt was sent
- **AND THEN** the command exits successfully

#### Scenario: Not-ready prompt refusal prints JSON error and exits non-zero
- **WHEN** an operator runs `houmao-mgr agents gateway prompt --agent-id abc123 --prompt "..."`
- **AND WHEN** the addressed target is not prompt-ready
- **AND WHEN** the operator did not pass `--force`
- **THEN** the command prints a structured JSON error payload
- **AND THEN** the command exits non-zero

#### Scenario: Force forwards prompt control override semantics
- **WHEN** an operator runs `houmao-mgr agents gateway prompt --agent-id abc123 --prompt "..." --force`
- **THEN** `houmao-mgr` forwards that request as forced prompt control
- **AND THEN** the command does not reject the prompt only because the target was not prompt-ready before dispatch

### Requirement: `houmao-mgr agents gateway` supports current-session targeting for same-session tmux operation
Gateway-targeting `houmao-mgr agents gateway ...` commands that operate on one managed agent SHALL support both explicit identity selectors and same-session current-session targeting.

At minimum, this SHALL apply to:

- `attach`
- `detach`
- `status`
- `prompt`
- `interrupt`
- `send-keys`
- `mail-notifier status`
- `mail-notifier enable`
- `mail-notifier disable`

When an operator omits explicit selectors and runs one of those commands inside the owning tmux session, `houmao-mgr` SHALL resolve the target through manifest-first current-session discovery using `HOUMAO_MANIFEST_PATH` or `HOUMAO_AGENT_ID`, and local resumed-control paths SHALL additionally recover `agent_def_dir` through `HOUMAO_AGENT_DEF_DIR` or shared-registry runtime metadata.

When a command supports current-session targeting, `houmao-mgr` MAY also expose an explicit `--current-session` switch, but it SHALL treat omitted selectors inside tmux as the same current-session targeting mode.

When an operator runs one of those commands outside tmux without explicit selectors, the command SHALL fail explicitly rather than guessing from cwd, gateway listener bindings, or ambient shell state.

#### Scenario: Same-session send-keys resolves from tmux discovery without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents gateway send-keys --sequence "<[Escape]>"` from inside the owning managed tmux session
- **AND WHEN** that tmux session publishes valid manifest-first discovery metadata
- **THEN** `houmao-mgr` resolves the current managed session through that tmux-local discovery contract
- **AND THEN** it sends the control-input request without requiring `--agent-id` or `--agent-name`

#### Scenario: Same-session notifier enable resolves from tmux discovery without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier enable --interval-seconds 60` from inside the owning managed tmux session
- **AND WHEN** that tmux session publishes valid manifest-first discovery metadata
- **THEN** `houmao-mgr` resolves the current managed session through that tmux-local discovery contract
- **AND THEN** it enables notifier behavior without requiring `--agent-id` or `--agent-name`

#### Scenario: Outside-tmux gateway control fails without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents gateway send-keys --sequence "<[Escape]>"` outside tmux
- **AND WHEN** the command is not given `--agent-id`, `--agent-name`, or `--current-session`
- **THEN** the command fails explicitly
- **AND THEN** it does not guess a managed-agent target from cwd or ambient shell state

### Requirement: `houmao-mgr agents gateway tui` exposes raw gateway-owned TUI tracking commands
`houmao-mgr` SHALL expose a native `agents gateway tui ...` command family for raw gateway-owned TUI tracking on managed agents.

At minimum, that family SHALL include:

- `state`
- `history`
- `watch`
- `note-prompt`

`agents gateway tui state` SHALL read the managed agent's live gateway-owned TUI state path rather than the transport-neutral managed-agent summary view.

`agents gateway tui history` SHALL read the managed agent's live gateway-owned bounded snapshot-history path rather than the coarse managed-agent `/history` surface.

`agents gateway tui note-prompt` SHALL target the managed agent's live gateway prompt-note tracking path rather than the queued gateway request path.

`agents gateway tui watch` SHALL act as an operator-facing repeated inspection surface over the same live gateway-owned TUI state path used by `agents gateway tui state`.

#### Scenario: Operator reads raw gateway-owned TUI state through the native `agents gateway tui` tree
- **WHEN** an operator runs `houmao-mgr agents gateway tui state --agent-id abc123`
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-mgr` returns the raw gateway-owned TUI state for that managed agent
- **AND THEN** the command does not collapse that response to the transport-neutral `agents state` payload

#### Scenario: Operator reads bounded snapshot history through the native `agents gateway tui` tree
- **WHEN** an operator runs `houmao-mgr agents gateway tui history --agent-id abc123`
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-mgr` returns the gateway-owned bounded recent TUI snapshot history for that managed agent
- **AND THEN** the command does not reinterpret that history as coarse managed-agent `/history`

#### Scenario: Operator records explicit prompt provenance without queue submission
- **WHEN** an operator runs `houmao-mgr agents gateway tui note-prompt --agent-id abc123 --prompt "..."`
- **AND WHEN** the addressed managed agent has an eligible live gateway attached
- **THEN** `houmao-mgr` records prompt-note evidence through the live gateway TUI tracking path
- **AND THEN** the command does not submit a queued gateway prompt request

### Requirement: `houmao-mgr agents gateway tui` supports the same managed-agent targeting contract as the rest of `agents gateway`
Gateway-targeting `houmao-mgr agents gateway tui ...` commands that operate on one managed agent SHALL support both explicit managed-agent selectors and same-session current-session targeting.

At minimum, this SHALL apply to:

- `state`
- `history`
- `watch`
- `note-prompt`

When an operator omits explicit selectors and runs one of those commands inside the owning tmux session, `houmao-mgr` SHALL resolve the target through the same manifest-first current-session discovery contract used by the rest of `agents gateway`.

When an operator runs one of those commands outside tmux without explicit selectors, the command SHALL fail explicitly rather than guessing from cwd, gateway listener bindings, or ambient shell state.

#### Scenario: Same-session gateway TUI state resolves from tmux discovery without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents gateway tui state` from inside the owning managed tmux session
- **AND WHEN** that tmux session publishes valid manifest-first discovery metadata
- **THEN** `houmao-mgr` resolves the current managed session through that tmux-local discovery contract
- **AND THEN** it reads the live gateway-owned TUI state without requiring `--agent-id` or `--agent-name`

#### Scenario: Outside-tmux gateway TUI watch fails without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents gateway tui watch` outside tmux
- **AND WHEN** the command is not given `--agent-id`, `--agent-name`, or `--current-session`
- **THEN** the command fails explicitly
- **AND THEN** it does not guess a managed-agent target from cwd or ambient shell state

### Requirement: Server-backed gateway raw control and notifier commands accept passive server pair authorities
`houmao-mgr` server-backed `agents gateway send-keys` and `agents gateway mail-notifier ...` command paths SHALL accept `houmao-passive-server` as a supported pair authority whenever those commands operate through an explicit pair authority instead of a resumed local controller.

For these commands, `houmao-mgr` SHALL resolve the pair client through the supported pair-authority factory and SHALL use the passive server's managed-agent gateway proxy routes rather than requiring direct listener discovery from the caller.

#### Scenario: Gateway raw control input works through a passive server
- **WHEN** an operator runs `houmao-mgr agents gateway send-keys --agent-id abc123 --port 9891 --sequence "<[Escape]>"`
- **AND WHEN** the addressed pair authority identifies `houmao-passive-server`
- **THEN** `houmao-mgr` sends that raw control-input request through the passive server's managed-agent gateway proxy route
- **AND THEN** the command does not fail only because the selected pair authority is passive

#### Scenario: Gateway mail notifier control works through a passive server
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier status --agent-id abc123 --port 9891`
- **AND WHEN** the addressed pair authority identifies `houmao-passive-server`
- **THEN** `houmao-mgr` reads notifier status through the passive server's managed-agent gateway proxy route
- **AND THEN** the command does not require the operator to contact the gateway listener endpoint directly

### Requirement: `houmao-mgr agents gateway attach` and `detach` preserve same-host passive-server support
When an operator targets a passive server for `houmao-mgr agents gateway attach` or `houmao-mgr agents gateway detach`, the CLI SHALL prefer local registry/controller authority for those operations instead of blindly calling the passive server's HTTP attach/detach routes.

If the target cannot be resolved to a local registry-backed authority on the current host, the CLI SHALL fail explicitly that passive-server gateway attach/detach is not available through remote pair HTTP control.

#### Scenario: Gateway attach succeeds through local authority while targeting a passive server
- **WHEN** an operator runs `houmao-mgr agents gateway attach --agent-id abc123 --port 9891`
- **AND WHEN** `abc123` can be resolved to a local registry/controller authority on the current host
- **THEN** `houmao-mgr` attaches or reuses the live gateway through that local authority
- **AND THEN** the command does not fail with the passive server's HTTP 501 guidance

#### Scenario: Gateway detach fails clearly when only remote passive authority is available
- **WHEN** an operator runs `houmao-mgr agents gateway detach --agent-id abc123 --port 9891`
- **AND WHEN** `abc123` cannot be resolved to a local registry/controller authority on the current host
- **THEN** `houmao-mgr` fails explicitly that passive-server gateway detach requires local authority on the owning host

### Requirement: `houmao-mgr agents turn events` renders canonical headless events with a detail selector
`houmao-mgr agents turn events` SHALL render canonical Houmao semantic headless turn events rather than raw provider stdout lines.

The command SHALL support `--detail concise|detail` with default `concise`.

For default `concise` rendering, the command SHALL replay the same semantic summary used by the live bridge path: answer text as the primary body, concise action request/result lines, and provider-exposed completion or usage accounting when available.

The command SHALL continue to honor the active root print style:

- `plain`: human-readable text summaries of canonical events
- `json`: canonical semantic JSON output
- `fancy`: rich human-readable rendering of canonical events

`detail` mode SHALL expose the extra structured event detail defined by the canonical headless event model.

For `plain` and `fancy` styles, the command SHALL replay canonical events using the same headless-domain renderer core used by the live bridge path for the selected `style` and `detail`.

#### Scenario: Default event inspection is human-readable and concise
- **WHEN** an operator runs `houmao-mgr agents turn events <agent-ref> <turn-id>` without overriding detail or root print style
- **THEN** the command renders concise human-readable summaries of canonical headless events
- **AND THEN** it does not print raw provider JSON lines by default
- **AND THEN** that concise summary includes answer text plus any available action lifecycle and completion-accounting lines defined by the canonical headless renderer contract

#### Scenario: JSON detail inspection exposes canonical structured event detail
- **WHEN** an operator runs `houmao-mgr --print-json agents turn events <agent-ref> <turn-id> --detail detail`
- **THEN** the command prints canonical semantic JSON for that turn's events
- **AND THEN** the output includes the extra structured detail defined for detail mode rather than raw provider stdout passthrough

#### Scenario: Plain replay matches live plain rendering semantics
- **WHEN** an operator inspects a turn whose live pane used `style=plain` and `detail=concise`
- **THEN** `houmao-mgr agents turn events` renders the same semantic summaries for assistant, tool, and completion events
- **AND THEN** any differences are limited to CLI transport framing rather than different event wording rules

#### Scenario: Replay reuses bridge renderer logic without owning the live process
- **WHEN** an operator replays one managed headless turn through `houmao-mgr agents turn events`
- **THEN** the command uses the same headless-domain renderer core as the live bridge path
- **AND THEN** it does so by replaying canonical events rather than by taking ownership of the provider subprocess used during live execution

### Requirement: Native headless artifact commands remain raw inspection surfaces
`houmao-mgr agents turn stdout` and `houmao-mgr agents turn stderr` SHALL remain raw artifact inspection commands for managed headless turns.

Those commands SHALL not reinterpret raw provider artifacts as canonical semantic events or rendered human output.

#### Scenario: Native stdout inspection returns raw provider artifact text
- **WHEN** an operator runs `houmao-mgr agents turn stdout <agent-ref> <turn-id>`
- **THEN** the command returns the raw stdout artifact text for that headless turn
- **AND THEN** it does not substitute canonical semantic JSON or rendered live-pane text for that raw artifact
- **AND THEN** the command does not falsely claim that remote passive-server HTTP detach succeeded

### Requirement: `houmao-mgr agents mail` exposes pair-native mailbox follow-up commands
`houmao-mgr` SHALL expose a native `agents mail ...` command family for mailbox discovery and follow-up on managed agents.

At minimum, that family SHALL include:

- `resolve-live`
- `status`
- `check`
- `send`
- `post`
- `reply`
- `mark-read`

Those commands SHALL address managed agents by managed-agent reference and SHALL dispatch mailbox work by the resolved managed-agent authority:

- pair-managed targets SHALL use pair-owned mail authority,
- local managed targets SHALL use verified manager-owned local mail authority or verified gateway-backed authority when available,
- when a local live-TUI target lacks verified direct or gateway authority for ordinary mailbox actions such as `check`, `send`, `reply`, or `mark-read`, the command MAY fall back to TUI-mediated submission and SHALL preserve a non-authoritative submission result instead of claiming mailbox success,
- operator-origin `post` SHALL NOT fall back to TUI-mediated submission and SHALL fail explicitly when verified manager-owned, pair-owned, or gateway-backed authority is unavailable,
- callers SHALL NOT be required to discover or call gateway endpoints directly themselves when using the CLI.

For commands in that family that operate on one managed agent, `houmao-mgr` SHALL support both explicit selectors and same-session current-session targeting:

- explicit `--agent-id` or `--agent-name` SHALL take precedence when provided,
- otherwise, when the caller runs the command inside the owning managed tmux session, `houmao-mgr` SHALL resolve the current managed agent through manifest-first discovery using `HOUMAO_MANIFEST_PATH` with `HOUMAO_AGENT_ID` as fallback,
- outside tmux without explicit selectors, the command SHALL fail explicitly rather than guessing from cwd or ambient shell state.

`resolve-live` SHALL return machine-readable mailbox binding and live gateway discovery data for the resolved managed agent.

For local managed targets, ordinary mailbox follow-up SHALL NOT require prompting the target agent to interpret mailbox instructions when verified manager-owned or gateway-backed mailbox execution is available.

#### Scenario: Same-session resolve-live succeeds without explicit selectors
- **WHEN** an operator or projected skill runs `houmao-mgr agents mail resolve-live` inside the owning managed tmux session
- **AND WHEN** that tmux session publishes valid manifest-first discovery metadata
- **THEN** `houmao-mgr` resolves the current managed agent through that tmux-local discovery contract
- **AND THEN** the command returns the current mailbox binding and any live gateway discovery data without requiring `--agent-id` or `--agent-name`

#### Scenario: Explicit selector wins over same-session discovery
- **WHEN** an operator runs `houmao-mgr agents mail status --agent-name alice` from inside a different managed tmux session
- **THEN** `houmao-mgr` targets the explicitly selected managed agent
- **AND THEN** the command does not silently replace that explicit target with the caller's current session

#### Scenario: Outside-tmux mail discovery fails without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents mail resolve-live` outside tmux
- **AND WHEN** the command is not given `--agent-id` or `--agent-name`
- **THEN** the command fails explicitly
- **AND THEN** it does not guess a managed-agent target from cwd, gateway listener bindings, or ambient shell state

#### Scenario: Local mail check uses manager-owned direct mailbox execution
- **WHEN** an operator runs `houmao-mgr agents mail check --agent-name alice`
- **AND WHEN** `alice` resolves to local managed-agent authority on the current host
- **THEN** `houmao-mgr` performs mailbox follow-up through manager-owned local mail authority
- **AND THEN** the command does not require prompting the target agent to interpret mailbox instructions for that ordinary mailbox check

#### Scenario: Local live-TUI send without verified direct authority returns submission-only fallback
- **WHEN** an operator runs `houmao-mgr agents mail send --agent-name alice --to bob@houmao.localhost --subject "..." --body-content "..."`
- **AND WHEN** `alice` resolves to a local live-TUI managed-agent target
- **AND WHEN** verified manager-owned or gateway-backed mail execution is unavailable for that action
- **THEN** `houmao-mgr` returns a non-authoritative submission result for that mailbox request
- **AND THEN** the command does not claim verified mailbox success solely from TUI transcript recovery

#### Scenario: Local live-TUI post without verified authority fails explicitly
- **WHEN** an operator runs `houmao-mgr agents mail post --agent-name alice --subject "..." --body-content "..."`
- **AND WHEN** `alice` resolves to a local live-TUI managed-agent target
- **AND WHEN** verified manager-owned or gateway-backed mail execution is unavailable for that action
- **THEN** the command fails explicitly instead of returning a submission-only mailbox result
- **AND THEN** it does not ask the target agent to impersonate `HOUMAO-operator@houmao.localhost`

#### Scenario: Pair-managed target still uses pair-owned mail authority
- **WHEN** an operator runs `houmao-mgr agents mail post --agent-id abc123 --subject "..." --body-content "..."`
- **AND WHEN** `abc123` resolves through pair authority
- **THEN** `houmao-mgr` dispatches that mailbox action through the supported pair-owned mail authority
- **AND THEN** the operator does not need to discover or address the pair-owned gateway endpoint directly

### Requirement: `houmao-mgr agents mailbox` exposes local late mailbox registration commands
`houmao-mgr` SHALL expose a native `agents mailbox ...` command family for late mailbox registration on existing local managed-agent sessions.

At minimum, that family SHALL include:

- `status`
- `register`
- `unregister`

Those commands SHALL target local managed-agent authority rather than pair-owned server mail authority.

#### Scenario: Operator uses a native late mailbox registration path under `agents`
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **THEN** `houmao-mgr` resolves `alice` through the local managed-agent discovery path
- **AND THEN** the command uses the local late mailbox registration workflow instead of requiring `houmao-server`

### Requirement: `houmao-mgr` renders expected mailbox-related operator failures without Python tracebacks
When a native `houmao-mgr` mailbox-management or gateway mail-notifier command hits an expected operator-facing failure, the CLI SHALL render that failure as explicit command-line error output rather than leaking a Python traceback from the top-level wrapper.

This SHALL apply at minimum to:

- `houmao-mgr agents mailbox register`
- `houmao-mgr agents mailbox unregister`
- `houmao-mgr agents mailbox status`
- `houmao-mgr agents mail ...`
- `houmao-mgr agents gateway mail-notifier status`
- `houmao-mgr agents gateway mail-notifier enable`
- `houmao-mgr agents gateway mail-notifier disable`

The wrapper SHALL preserve the command's non-zero exit behavior for those failures.
This requirement covers expected operator-facing failures such as explicit Click-style usage errors, manifest/runtime readiness errors, and gateway readiness errors that the command path already classifies as normal command failures.
The CLI SHALL NOT claim success or hide the failure reason; it SHALL surface the explicit operator-facing error text without the Python stack trace.

#### Scenario: Joined mailbox registration failure renders as a clean CLI error
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** the command fails with an expected operator-facing mailbox-registration error
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports the failure as clean CLI error text without a Python traceback

#### Scenario: Gateway mail-notifier enable failure renders as a clean CLI error
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier enable --agent-name alice --interval-seconds 60`
- **AND WHEN** the command fails with an expected operator-facing gateway notifier readiness error
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports the failure as clean CLI error text without a Python traceback

### Requirement: `houmao-mgr agents turn` exposes managed headless turn commands
`houmao-mgr` SHALL expose a native `agents turn ...` command family for managed headless turn submission and inspection.

At minimum, that family SHALL include:

- `submit`
- `status`
- `events`
- `stdout`
- `stderr`

Those commands SHALL use the managed headless turn routes exposed by the supported pair authority.

#### Scenario: Operator submits a managed headless turn through the native `agents turn` tree
- **WHEN** an operator runs `houmao-mgr agents turn submit <agent-ref> --prompt "..." `
- **THEN** `houmao-mgr` submits that prompt through the managed headless turn authority
- **AND THEN** the command returns the accepted turn identity needed for later inspection

#### Scenario: TUI-backed agent rejects native headless turn submission
- **WHEN** an operator runs `houmao-mgr agents turn submit <agent-ref> --prompt "..." `
- **AND WHEN** the addressed managed agent is TUI-backed
- **THEN** the command fails explicitly
- **AND THEN** it does not pretend that the TUI-backed agent supports the headless turn contract

### Requirement: Server-backed managed-agent commands accept passive server pair authorities
`houmao-mgr` server-backed managed-agent command paths SHALL accept `houmao-passive-server` as a supported pair authority and SHALL resolve their managed client through the pair-authority factory.

This SHALL cover the `agents`, `agents mail`, and `agents turn` families whenever those commands are operating through an explicit pair authority instead of a resumed local controller.

#### Scenario: Managed-agent summary inspection works through a passive server
- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123 --port 9891`
- **AND WHEN** the addressed pair authority identifies `houmao-passive-server`
- **THEN** `houmao-mgr` returns the managed-agent summary view for `abc123`
- **AND THEN** the command does not fail only because the selected pair authority is passive

#### Scenario: Headless turn submission works through a passive server
- **WHEN** an operator runs `houmao-mgr agents turn submit --agent-id abc123 --port 9891 --prompt "..." `
- **AND WHEN** the addressed pair authority identifies `houmao-passive-server`
- **THEN** `houmao-mgr` submits the turn through the passive server
- **AND THEN** the command returns the accepted turn identity needed for later inspection

### Requirement: `houmao-mgr brains build` exposes local brain construction
`houmao-mgr` SHALL expose a native `brains build` command for local brain construction.

`brains build` SHALL remain a local artifact-building command rather than a `houmao-server` API operation.

At minimum, that command SHALL support the local build inputs and outputs needed to construct a brain home and return its manifest and launch-helper pointers.

#### Scenario: Operator builds a brain without requiring `houmao-server`
- **WHEN** an operator runs `houmao-mgr brains build ...`
- **THEN** `houmao-mgr` materializes the requested local brain artifacts on the local host
- **AND THEN** the command does not require a running `houmao-server` instance just to build those artifacts

### Requirement: Native `houmao-mgr` expansion retires `cao` namespace and top-level `launch`
Expanding `houmao-mgr` SHALL retire the `cao` command group and the top-level `launch` command entirely.

- `houmao-mgr cao *` commands SHALL be removed from the supported command tree.
- Top-level `houmao-mgr launch` SHALL be removed. Agent launch moves to `houmao-mgr agents launch`.
- The `server` group replaces server-lifecycle commands previously under `cao` (info, shutdown).
- The `agents launch` command replaces `cao launch` and top-level `launch`.

Repo-owned docs, tests, examples, and scripts SHALL use `houmao-mgr agents launch` and `houmao-mgr server *` rather than `cao launch` or top-level `launch`.

#### Scenario: `cao` namespace is no longer available
- **WHEN** an operator runs `houmao-mgr cao launch --agents ...`
- **THEN** the command fails because `cao` is not a recognized command group
- **AND THEN** help text does not list `cao` as an option

#### Scenario: Top-level launch is no longer available
- **WHEN** an operator runs `houmao-mgr launch --agents ...`
- **THEN** the command fails because `launch` is not a recognized top-level command
- **AND THEN** the operator is directed to use `houmao-mgr agents launch` instead

#### Scenario: Repo-owned scripts use the new command paths
- **WHEN** repo-owned scripts, tests, or docs reference agent launch
- **THEN** they use `houmao-mgr agents launch` rather than `houmao-mgr cao launch` or `houmao-mgr launch`

### Requirement: Repo-owned docs prefer `houmao-mgr` over `houmao-cli` for covered pair workflows
Repo-owned active documentation under `docs/` SHALL present `houmao-mgr` and `houmao-server` as the supported operator surfaces for current managed-agent and pair workflows.

References to `houmao-cli` MAY remain only in explicit migration, legacy, retirement, or historical contexts. Active documentation SHALL NOT retain `houmao-cli` as the default example for uncovered current workflows just because a native replacement has not been implemented yet.

Repo-owned documentation for managed-agent inspection SHALL NOT present `houmao-mgr agents history` as a supported native inspection surface.

#### Scenario: Active docs replace `houmao-cli` examples for supported workflows
- **WHEN** a repo-owned document under `docs/` describes a current managed-agent or pair workflow that is supported by `houmao-mgr` or `houmao-server`
- **THEN** that document uses `houmao-mgr` or `houmao-server` as the primary command example
- **AND THEN** it does not keep `houmao-cli` as the default example for that workflow

#### Scenario: Legacy `houmao-cli` references are explicitly marked as legacy
- **WHEN** a repo-owned document under `docs/` still mentions `houmao-cli`
- **THEN** that mention appears only in explicit migration, legacy, retirement, or historical guidance
- **AND THEN** it is not presented as an active default operator path

#### Scenario: Docs do not present retired managed-agent inspection commands
- **WHEN** repo-owned docs under `docs/` explain managed-agent inspection or long-running local/serverless operation
- **THEN** they use supported surfaces such as `houmao-mgr agents state`, gateway TUI state, or `houmao-mgr agents turn ...`
- **AND THEN** they do not present `houmao-mgr agents show` or `houmao-mgr agents history` as supported native inspection commands

### Requirement: `houmao-mgr agents relaunch` exposes tmux-backed managed-session recovery
`houmao-mgr` SHALL expose `agents relaunch` as the native managed-session recovery command for tmux-backed managed agents.

`agents relaunch` SHALL support both explicit targeting by managed-agent identity and a current-session mode when the operator runs the command from inside the owning tmux session.

The command SHALL resolve the target session through manifest-first discovery, SHALL reuse the persisted session and built home, and SHALL NOT route through build-time `houmao-mgr agents launch`.

The command SHALL fail explicitly when the target is not tmux-backed, lacks valid manifest-owned relaunch authority, or cannot be resolved through supported selector or current-session discovery.

#### Scenario: Current-session relaunch uses tmux-local discovery
- **WHEN** an operator runs `houmao-mgr agents relaunch` from inside a tmux-backed managed session
- **THEN** `houmao-mgr` resolves that session through `HOUMAO_MANIFEST_PATH` or `HOUMAO_AGENT_ID`
- **AND THEN** it relaunches the managed agent surface without requiring an explicit selector

#### Scenario: Explicit relaunch uses managed-agent identity
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **THEN** `houmao-mgr` resolves that live agent through registry-first discovery or the supported pair authority
- **AND THEN** it relaunches the existing tmux-backed managed session instead of creating a new launch

#### Scenario: Non-tmux-backed target fails clearly
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **AND WHEN** the resolved managed agent is not a tmux-backed relaunchable session
- **THEN** the command fails explicitly
- **AND THEN** it does not pretend that build-time launch or a raw CAO path is a supported replacement

### Requirement: Managed-agent-targeting native CLI commands use explicit identity selectors

`houmao-mgr agents` commands that target one managed agent SHALL accept explicit identity selectors instead of relying on one positional managed-agent reference.

At minimum, managed-agent-targeting commands in the `agents`, `agents gateway`, `agents mail`, and `agents turn` families SHALL accept:

- `--agent-id <id>`
- `--agent-name <name>`

For these commands, callers SHALL provide exactly one of those selectors unless the command defines a separate current-session targeting contract.

`--agent-id` SHALL target the authoritative globally unique managed-agent identity.

`--agent-name` SHALL target the friendly managed-agent name and SHALL only succeed when the relevant authority can prove that exactly one live managed agent currently uses that name.

When local registry-first discovery finds no live managed agent whose friendly name matches the supplied `--agent-name`, the command SHALL preserve that selector-miss context in any resulting failure instead of surfacing only a later transport-level fallback failure.

If the command cannot complete fallback lookup through the default pair authority after such a local miss, it SHALL report both the local friendly-name miss and the remote lookup unavailability, and SHALL direct the operator toward a corrective retry path such as `houmao-mgr agents list`, the correct friendly managed-agent name, or `--agent-id`.

If the supplied `--agent-name` exactly matches one unique live local tmux/session alias but not that agent's friendly managed-agent name, the command SHALL state that `--agent-name` expects the friendly managed-agent name and SHALL direct the operator to retry with the published `agent_name` or `--agent-id`.

#### Scenario: Exact selector by agent id is accepted

- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123`
- **THEN** `houmao-mgr` targets the managed agent whose authoritative identity is `abc123`
- **AND THEN** the operator does not need to rely on friendly-name uniqueness for that control action

#### Scenario: Friendly-name selector succeeds only when unique

- **WHEN** an operator runs `houmao-mgr agents state --agent-name gpu`
- **AND WHEN** exactly one live managed agent currently uses friendly name `gpu`
- **THEN** `houmao-mgr` targets that managed agent
- **AND THEN** the command succeeds without requiring the operator to spell the authoritative `agent_id`

#### Scenario: Friendly-name selector fails on ambiguity

- **WHEN** an operator runs `houmao-mgr agents prompt --agent-name gpu --prompt "..."`
- **AND WHEN** more than one live managed agent currently uses friendly name `gpu`
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error directs the operator to retry with `--agent-id`

#### Scenario: Friendly-name miss reports local miss before remote-unavailable fallback

- **WHEN** an operator runs `houmao-mgr agents state --agent-name agent-test`
- **AND WHEN** no live local managed agent currently uses friendly name `agent-test`
- **AND WHEN** the default pair authority is unavailable for fallback lookup
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error states that no local managed agent matched friendly name `agent-test`
- **AND THEN** the error also states that remote pair-authority lookup could not complete
- **AND THEN** the error does not present pair-authority unavailability as the only problem

#### Scenario: Friendly-name selector that matches a tmux/session alias gives a corrective hint

- **WHEN** an operator runs `houmao-mgr agents state --agent-name agent-test`
- **AND WHEN** no live local managed agent currently uses friendly name `agent-test`
- **AND WHEN** exactly one live local managed agent uses tmux/session alias `agent-test`
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error states that `--agent-name` expects the friendly managed-agent name rather than the tmux/session alias
- **AND THEN** the error identifies the matching agent's published friendly name or authoritative `agent_id` as the retry target

#### Scenario: Missing selector fails when no current-session contract applies

- **WHEN** an operator runs `houmao-mgr agents stop` without `--agent-id` or `--agent-name`
- **AND WHEN** that command has no separate current-session targeting contract
- **THEN** `houmao-mgr` fails explicitly
- **AND THEN** the error states that exactly one of `--agent-id` or `--agent-name` is required

### Requirement: `houmao-mgr agents gateway attach` defaults tmux-backed managed sessions to foreground tmux-window mode with explicit background opt-out
`houmao-mgr agents gateway attach` SHALL default tmux-backed managed sessions to same-session foreground tmux-window mode.

`houmao-mgr agents gateway attach` SHALL accept an explicit `--background` option for tmux-backed managed sessions.

When no `--background` override is supplied for a runtime-owned tmux-backed managed session, `houmao-mgr` SHALL attach or reuse the gateway in same-session foreground tmux-window mode rather than detached-process mode.

When no `--background` override is supplied for a pair-managed `houmao_server_rest` session, `houmao-mgr` SHALL treat the attach as the standard same-session auxiliary-window topology for that managed session.

When `--background` is requested for a tmux-backed managed session, `houmao-mgr` SHALL attach or reuse the gateway in detached background execution rather than same-session foreground tmux-window mode.

When foreground tmux-window mode is active, `houmao-mgr agents gateway attach` and `houmao-mgr agents gateway status` SHALL surface the gateway execution mode and the authoritative tmux window index for the live gateway surface so operators can inspect that console directly.

Foreground tmux-window mode SHALL NOT redefine the managed agent attach contract: tmux window `0` remains reserved for the agent surface, and the gateway window SHALL use index `>=1`.

#### Scenario: Default gateway attach uses foreground mode for a runtime-owned tmux-backed session
- **WHEN** an operator runs `houmao-mgr agents gateway attach --agent-id <id>`
- **AND WHEN** the addressed managed session is a runtime-owned tmux-backed session
- **THEN** `houmao-mgr` attaches or reuses the gateway in same-session foreground tmux-window mode
- **AND THEN** the command reports the actual tmux window index for the live gateway surface

#### Scenario: Default gateway attach preserves the pair-managed same-session topology
- **WHEN** an operator runs `houmao-mgr agents gateway attach --agent-id <id>`
- **AND WHEN** the addressed managed session is a pair-managed `houmao_server_rest` session
- **THEN** `houmao-mgr` attaches or reuses the gateway in same-session foreground tmux-window mode
- **AND THEN** the command reports the actual tmux window index for the live gateway surface

#### Scenario: Operator requests background gateway attach
- **WHEN** an operator runs `houmao-mgr agents gateway attach --background --agent-id <id>`
- **AND WHEN** the addressed managed session is tmux-backed and gateway-capable
- **THEN** `houmao-mgr` attaches or reuses the gateway in detached background execution
- **AND THEN** the attach result does not claim a foreground tmux gateway window for that attach

#### Scenario: Operator inspects foreground gateway status through the native CLI
- **WHEN** an operator runs `houmao-mgr agents gateway status --agent-id <id>`
- **AND WHEN** the addressed gateway is running in foreground tmux-window mode
- **THEN** the command reports `execution_mode=tmux_auxiliary_window`
- **AND THEN** the command reports the authoritative tmux window index for the live gateway surface

#### Scenario: Foreground attach preserves the agent surface contract
- **WHEN** a tmux-backed managed session runs with foreground gateway execution active
- **THEN** the gateway attaches in a tmux window whose index is `>=1`
- **AND THEN** tmux window `0` remains the managed agent surface

### Requirement: `houmao-mgr admin cleanup` exposes grouped local cleanup commands
`houmao-mgr` SHALL expose a native `admin cleanup` command group for local cleanup operations.

At minimum, the documented grouped cleanup tree SHALL include:

- `registry`
- `runtime sessions`
- `runtime builds`
- `runtime logs`
- `runtime mailbox-credentials`

This grouped cleanup tree SHALL be documented as local maintenance over local Houmao-owned state rather than as a pair-managed server API surface.

Within that grouped tree, `houmao-mgr admin cleanup registry` SHALL perform local tmux liveness probing by default for tmux-backed records and SHALL expose `--no-tmux-check` as the explicit opt-out flag for lease-only behavior.

#### Scenario: Native admin help surface shows only grouped cleanup entry
- **WHEN** an operator runs `houmao-mgr admin --help`
- **THEN** the help output lists `cleanup`
- **AND THEN** the help output does not list `cleanup-registry` as a sibling command

#### Scenario: Native help surface shows grouped cleanup commands
- **WHEN** an operator runs `houmao-mgr admin cleanup --help`
- **THEN** the help output lists `registry` and the `runtime` cleanup family
- **AND THEN** the grouped cleanup surface is presented as local maintenance rather than a server-backed admin API

#### Scenario: Registry cleanup help shows the opt-out tmux flag
- **WHEN** an operator runs `houmao-mgr admin cleanup registry --help`
- **THEN** the help output includes `--no-tmux-check`
- **AND THEN** the help output does not require `--probe-local-tmux` to enable default tmux probing

#### Scenario: Registry cleanup defaults to tmux probing
- **WHEN** an operator runs `houmao-mgr admin cleanup registry`
- **AND WHEN** a lease-fresh tmux-backed registry record points at a tmux session that is absent on the local host
- **THEN** `houmao-mgr` classifies that record as stale by default
- **AND THEN** the operator does not need an extra flag to perform local tmux-aware cleanup

#### Scenario: Legacy cleanup-registry path is no longer supported
- **WHEN** an operator runs `houmao-mgr admin cleanup-registry`
- **THEN** the command fails because `cleanup-registry` is not a recognized native admin subcommand
- **AND THEN** the operator is directed to use `houmao-mgr admin cleanup registry`

### Requirement: `houmao-mgr agents cleanup` exposes local managed-session cleanup commands
`houmao-mgr` SHALL expose a native `agents cleanup` command family for local managed-session cleanup.

At minimum, that family SHALL include:

- `session`
- `logs`
- `mailbox`

These commands SHALL operate through local runtime-owned authority rather than a pair-managed server authority.

When the operator does not pass an explicit cleanup target and runs the command from inside the owning tmux session, the command family SHALL support current-session targeting through manifest-first discovery.

#### Scenario: Native help surface shows agent-scoped cleanup commands
- **WHEN** an operator runs `houmao-mgr agents cleanup --help`
- **THEN** the help output lists `session`, `logs`, and `mailbox`
- **AND THEN** the family is described as local managed-session cleanup rather than as a remote pair-managed request path

#### Scenario: Agent-scoped cleanup can default to current-session authority
- **WHEN** an operator runs `houmao-mgr agents cleanup logs` from inside the tmux session that hosts the managed agent
- **THEN** `houmao-mgr` resolves that cleanup target through supported current-session manifest authority
- **AND THEN** the operator does not need to spell the target session again just to clean its local artifacts

### Requirement: `houmao-mgr mailbox messages` reports structural mailbox message inspection

The native `houmao-mgr mailbox messages list` and `houmao-mgr mailbox messages get` commands SHALL act as structural inspection over one filesystem mailbox root and one selected mailbox address.

Those commands MAY return canonical message metadata and address-scoped projection metadata for the selected address, including message identity, thread identity, projection folder, projection path, canonical path, sender metadata, recipient metadata, body content, headers, and attachments.

Those commands SHALL NOT report participant-local mutable mailbox view-state fields such as `read`, `starred`, `archived`, or `deleted`.

When an operator needs participant-local read or unread follow-up state, the supported surface SHALL be actor-scoped mail commands such as `houmao-mgr agents mail ...` or a future explicitly address-scoped state surface rather than mailbox-root administration commands.

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

### Requirement: `houmao-mgr project mailbox messages` reuses the structural mailbox inspection contract

The native `houmao-mgr project mailbox messages list` and `houmao-mgr project mailbox messages get` commands SHALL expose the same structural-only message inspection contract as `houmao-mgr mailbox messages list|get`, but fixed to the current project's `.houmao/mailbox` root.

Those project-scoped wrappers SHALL NOT add or reintroduce participant-local mutable mailbox view-state fields removed from the root-level mailbox command family.

#### Scenario: Project mailbox message list matches the structural inspection contract

- **WHEN** an operator runs `houmao-mgr project mailbox messages list --address alice@agents.localhost`
- **THEN** the command returns structural message summaries for the selected project-local address projection
- **AND THEN** the payload shape matches the root-level structural mailbox message summary contract
- **AND THEN** the payload does not include `read`, `starred`, `archived`, or `deleted`

#### Scenario: Project mailbox message get matches the structural inspection contract

- **WHEN** an operator runs `houmao-mgr project mailbox messages get --address alice@agents.localhost --message-id msg-123`
- **THEN** the command returns canonical message details together with the selected project-local address projection metadata
- **AND THEN** the payload shape matches the root-level structural mailbox message detail contract
- **AND THEN** the payload does not claim a single authoritative participant-local read, starred, archived, or deleted state

### Requirement: `houmao-mgr agents gateway` exposes `--target-tmux-session` for explicit outside-tmux targeting
Gateway-targeting `houmao-mgr agents gateway ...` commands that operate on one managed agent SHALL accept `--target-tmux-session <tmux-session-name>` as an explicit selector in addition to the existing `--agent-id`, `--agent-name`, and same-session current-session modes.

At minimum, this SHALL apply to:

- `attach`
- `detach`
- `status`
- `prompt`
- `interrupt`
- `send-keys`
- `mail-notifier status`
- `mail-notifier enable`
- `mail-notifier disable`

For those commands, `houmao-mgr` SHALL name the explicit pair-authority override `--pair-port` rather than `--port`.

For those commands, `houmao-mgr` SHALL accept exactly one of `--agent-id`, `--agent-name`, `--target-tmux-session`, or `--current-session`, except that omitted selectors inside the owning tmux session SHALL remain equivalent to current-session targeting.

`--pair-port` SHALL remain valid only with `--agent-id` or `--agent-name`. The CLI SHALL reject `--pair-port` when the operator selects `--target-tmux-session` or `--current-session`.

The help text and error messaging for `--pair-port` SHALL describe it as the Houmao pair-authority port so operators do not confuse it with gateway listener port overrides such as lower-level `--gateway-port`.

When an operator runs one of those commands outside tmux with `--target-tmux-session`, `houmao-mgr` SHALL resolve the local managed-agent target through the addressed tmux session authority and SHALL NOT require `--agent-id` or `--agent-name`.

#### Scenario: Outside-tmux gateway status resolves by explicit tmux session selector
- **WHEN** an operator runs `houmao-mgr agents gateway status --target-tmux-session HOUMAO-gpu-coder-1-1775467167530`
- **AND WHEN** the addressed tmux session resolves to one live managed-agent target on the local host
- **THEN** `houmao-mgr` resolves that target without requiring `--agent-id` or `--agent-name`
- **AND THEN** it returns gateway status for the addressed managed session

#### Scenario: Gateway prompt supports the tmux-session selector across the command family
- **WHEN** an operator runs `houmao-mgr agents gateway prompt --target-tmux-session HOUMAO-gpu-coder-1-1775467167530 --prompt "hi"`
- **AND WHEN** the addressed tmux session resolves to one live managed-agent target on the local host
- **THEN** `houmao-mgr` submits the gateway-mediated prompt to that resolved target
- **AND THEN** the operator does not need to rediscover the managed-agent id before using the follow-up gateway command

#### Scenario: Port override is rejected for tmux-session targeting
- **WHEN** an operator runs `houmao-mgr agents gateway attach --target-tmux-session HOUMAO-gpu-coder-1-1775467167530 --pair-port 9891`
- **THEN** `houmao-mgr` rejects that invocation explicitly
- **AND THEN** the command explains that `--pair-port` is only supported with explicit `--agent-id` or `--agent-name` targeting

#### Scenario: Explicit pair-authority override uses the clearer flag name
- **WHEN** an operator runs `houmao-mgr agents gateway status --agent-id abc123 --pair-port 9891`
- **THEN** `houmao-mgr` targets the pair authority at port `9891`
- **AND THEN** the command surface does not describe that override as a generic `--port` that could be mistaken for the gateway listener port

### Requirement: `houmao-mgr agents interrupt` keeps TUI interrupt transport-neutral
`houmao-mgr agents interrupt` SHALL keep one transport-neutral operator contract across managed-agent transports.

For TUI-backed managed agents, the command SHALL dispatch one best-effort `Escape` interrupt signal through the resolved managed-agent control authority and SHALL NOT require the operator to know or supply raw TUI key semantics.

For TUI-backed managed agents, the command SHALL NOT reject or no-op solely because coarse tracked TUI phase currently reports `idle` or another non-active posture.

For headless managed agents, the command SHALL continue using the managed execution interrupt path and MAY return no-op behavior when no headless work is active.

#### Scenario: Operator interrupts a server-backed TUI agent without tracking-phase veto
- **WHEN** an operator runs `houmao-mgr agents interrupt --agent-id abc123` for a managed TUI agent
- **AND WHEN** the resolved managed-agent control path is reachable
- **AND WHEN** coarse tracked TUI phase is currently non-active
- **THEN** `houmao-mgr` still submits one best-effort TUI interrupt request
- **AND THEN** the operator is not forced to switch to a raw `send-keys` command just to deliver `Escape`

#### Scenario: Operator interrupt keeps headless no-op semantics
- **WHEN** an operator runs `houmao-mgr agents interrupt --agent-id abc123` for a managed headless agent with no active execution
- **THEN** `houmao-mgr` returns the headless interrupt no-op result
- **AND THEN** the command does not fabricate a delivered TUI-style `Escape` interrupt for headless state

### Requirement: Native managed-agent local resume failures render as clean CLI errors

When a native `houmao-mgr agents ...` command resolves a local managed-agent target through shared-registry metadata and local controller resume fails with an expected realm-controller runtime-domain failure, `houmao-mgr` SHALL render that failure as explicit CLI error output rather than leaking a Python traceback.

This SHALL apply at minimum to local managed-agent commands that resume a local controller before dispatch, including:

- `houmao-mgr agents stop`
- `houmao-mgr agents prompt`
- `houmao-mgr agents interrupt`
- `houmao-mgr agents relaunch`

For stale tmux-backed local targets, the rendered failure SHALL preserve non-zero exit behavior and SHALL explain that the selected managed agent's local tmux-backed runtime authority is no longer live or otherwise unusable.

#### Scenario: Stale tmux-backed local stop target fails without traceback
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name alice`
- **AND WHEN** registry-first local discovery resolves managed agent `alice`
- **AND WHEN** local controller resume fails because the persisted tmux session for that managed agent no longer exists
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports a managed-agent contextual CLI error explaining that the local runtime authority is unusable
- **AND THEN** stderr does not include a Python traceback

#### Scenario: Local prompt target runtime failure still renders as CLI error text
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id agent-123 --prompt "hello"`
- **AND WHEN** registry-first local discovery resolves that managed agent
- **AND WHEN** local controller resume fails with an expected realm-controller runtime-domain error
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports the failure as explicit CLI error text for that managed agent
- **AND THEN** stderr does not include a Python traceback

### Requirement: `houmao-mgr` headless prompt commands expose request-scoped execution override flags
The native `houmao-mgr` prompt submission surfaces for headless work SHALL expose request-scoped execution override flags.

At minimum, this SHALL apply to:

- `houmao-mgr agents turn submit`
- `houmao-mgr agents gateway prompt`
- `houmao-mgr agents prompt`

Those commands SHALL accept:

- `--model <name>`
- `--reasoning-level <1..10>`

When either flag is supplied, the CLI SHALL construct request-scoped `execution.model` payload with the supplied subfields and omit unsupplied subfields so the server or gateway can inherit the remaining values from launch-resolved defaults.

`houmao-mgr agents turn submit` SHALL send that payload through the managed headless turn route.

`houmao-mgr agents gateway prompt` SHALL send that payload through the managed gateway direct prompt-control path.

`houmao-mgr agents prompt` SHALL send that payload through the transport-neutral managed-agent prompt path.

Before dispatch, `houmao-mgr agents gateway prompt` and `houmao-mgr agents prompt` SHALL resolve the addressed managed agent and reject these execution flags clearly when the resolved target is TUI-backed rather than silently dropping them.

#### Scenario: Managed headless turn submit accepts both execution flags
- **WHEN** an operator runs `houmao-mgr agents turn submit --agent-id abc123 --prompt "review this" --model gpt-5.4-mini --reasoning-level 4`
- **THEN** `houmao-mgr` submits the managed headless turn successfully
- **AND THEN** the request includes `execution.model.name = "gpt-5.4-mini"` and `execution.model.reasoning.level = 4`

#### Scenario: Transport-neutral prompt forwards partial execution override for a headless target
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id abc123 --prompt "review this" --reasoning-level 2`
- **AND WHEN** the resolved managed agent is headless
- **THEN** `houmao-mgr` submits that prompt through the supported transport-neutral managed-agent path
- **AND THEN** the request includes only the partial execution override for reasoning level `2`

#### Scenario: Gateway prompt rejects execution override for a TUI target
- **WHEN** an operator runs `houmao-mgr agents gateway prompt --agent-id abc123 --prompt "review this" --model gpt-5.4-mini`
- **AND WHEN** the resolved managed agent is TUI-backed
- **THEN** `houmao-mgr` fails that command clearly
- **AND THEN** it does not silently send a TUI gateway prompt while dropping the requested model override

#### Scenario: Invalid reasoning-level flag is rejected clearly
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id abc123 --prompt "review this" --reasoning-level 0`
- **THEN** `houmao-mgr` rejects that input clearly
- **AND THEN** the CLI does not construct or send an invalid request payload
