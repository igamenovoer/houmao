## Purpose
Define the Houmao-owned native `houmao-mgr` command tree for covered pair workflows, including server-backed managed-agent operations and local utility commands.
## Requirements
### Requirement: `houmao-mgr` exposes a native pair-operations command tree
`houmao-mgr` SHALL expose a Houmao-owned root command tree. Bare invocation SHALL print help. Root options SHALL control output style and report the packaged version. Help SHALL link the published documentation.

#### Scenario: Root command families are documented
- **WHEN** the manager exposes its root command tree
- **THEN** it includes `server`, `agents`, `brains`, `credentials`, `admin`, `mailbox`, `project`, and `system-skills`
- **AND THEN** the documentation identifies each as a Houmao-owned pair command or local operator command
- **AND THEN** `cao` and top-level `launch` are absent

#### Scenario: Root flags configure formatting for subcommands
- **WHEN** a caller selects `--print-plain`, `--print-json`, or `--print-fancy`
- **THEN** the root treats the options as mutually exclusive flag values
- **AND THEN** the selected style controls formatting for all subcommands through an `OutputContext` in `click.Context.obj["output"]`

#### Scenario: The root group handles no-argument invocation
- **WHEN** the entrypoint configures the root group
- **THEN** it sets `invoke_without_command=True` to enable bare-invocation help

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
`houmao-mgr agents` SHALL be the preferred pair-native family for managing agents by identity. `join` SHALL adopt an existing tmux-backed session, and `state` SHALL present the operational summary for managed-agent inspection.

#### Scenario: The agents family exposes managed operations
- **WHEN** a caller works through the native agents family
- **THEN** it exposes `launch`, `join`, `list`, `state`, `prompt`, `interrupt`, `relaunch`, and `stop`
- **AND THEN** managed-agent identity is the addressing model rather than raw `terminal_id` or a raw CAO session name
- **AND THEN** joining requires neither `houmao-server` nor raw tmux attach scripts
- **AND THEN** managed-agent inspection does not require or advertise `show` or `history`

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
`houmao-mgr` SHALL expose `agents gateway` for gateway lifecycle and operations against the live gateway. Ordinary pair-native prompts SHALL be documented through `houmao-mgr agents prompt`.

#### Scenario: Gateway operations are exposed
- **WHEN** a caller selects the native gateway family
- **THEN** the family provides `attach`, `detach`, `status`, `prompt`, `interrupt`, `send-keys`, and `mail-notifier status|enable|disable`

#### Scenario: Gateway prompt and interrupt select live routes
- **WHEN** a caller uses `agents gateway prompt` or `interrupt`
- **THEN** `prompt` uses direct live gateway prompt control instead of a transport-neutral or queued request
- **AND THEN** `interrupt` uses live gateway-mediated interruption
- **AND THEN** the documentation describes the direct prompt route and its named admission policies

#### Scenario: Gateway keys and notifier select dedicated controls
- **WHEN** a caller uses `agents gateway send-keys` or `mail-notifier`
- **THEN** `send-keys` uses live raw control input without queueing, prompt-readiness gating, or busy gating
- **AND THEN** `mail-notifier` uses the live gateway notifier control instead of foreground managed-agent mail

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
`houmao-mgr agents gateway reminders` SHALL expose `list`, `get`, `create`, `set`, and `remove` through managed-agent resolution and live gateway authority. `create` SHALL accept one definition per invocation. `set` SHALL target one existing reminder by `--reminder-id`.

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
Gateway reminder operations SHALL use the same local registry aliases, explicit agent selectors, and verified self authority as other gateway operations. Explicit pair selection SHALL support the maintained passive server.

#### Scenario: Reminder operations accept the standard gateway selectors

- **WHEN** an operator lists reminders with an explicit local registry alias
- **THEN** the command uses the uniquely selected owner

#### Scenario: Current-session reminder inspection resolves the owning managed session

- **WHEN** an agent runs `houmao-mgr agents self gateway reminders list`
- **THEN** the command uses the current runtime's verified manifest and signer

#### Scenario: Pair-backed reminder creation works through passive-server authority

- **WHEN** an operator creates a reminder with an explicit agent ID and `--pair-port`
- **AND WHEN** the addressed pair authority reports `houmao_service == "houmao-passive-server"`
- **THEN** the manager routes the create request through the addressed agent's passive-server gateway proxy

### Requirement: `houmao-mgr agents gateway reminders create` and `set` support numeric ranking plus prepend and append placement modes
Reminder `create` SHALL require one numeric ranking mode, and `set` SHALL accept at most one. The supported modes SHALL be `--ranking <int>`, `--before-all`, and `--after-all`. The CLI SHALL exclude named priority aliases such as `high`, `normal`, and `low`.

#### Scenario: Ranking placement resolves against the live set
- **WHEN** a caller requests `--before-all` or `--after-all`
- **THEN** the CLI computes one less than the smallest ranking or one more than the largest ranking, respectively
- **AND THEN** either placement resolves to `0` when the set is empty

#### Scenario: Setting fields preserves an omitted ranking and other fields
- **WHEN** a caller runs reminder `set` without specifying a ranking or other existing fields
- **THEN** the CLI preserves every unspecified field and the existing ranking
- **AND THEN** the gateway receives a full replacement `PUT` after the CLI applies the partial update

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

### Requirement: `houmao-mgr agents gateway` supports current-session targeting for same-session tmux operation
Gateway commands that address one managed agent SHALL support existing explicit and current-session target scopes. Current-session targeting SHALL discover and verify the owning session through its manifest. Gateway operations SHALL use the verified manifest's runtime authority and current gateway binding.

#### Scenario: Gateway current-session targeting applies to managed operations
- **WHEN** a caller uses `attach`, `detach`, `status`, `prompt`, `interrupt`, `send-keys`, or `mail-notifier status|enable|disable` inside the owning tmux session
- **THEN** current-session scope selects that session
- **AND THEN** the CLI discovers the manifest through `HOUMAO_MANIFEST_PATH` or the live record named by `HOUMAO_AGENT_ID`
- **AND THEN** it performs the supported gateway operation using published runtime authority without reading the definition directory

#### Scenario: Current-session targeting requires the owning tmux session
- **WHEN** a caller requests tmux-backed current-session targeting without a verified binding to the owning tmux session
- **THEN** the CLI reports a missing target without guessing from cwd, gateway listener bindings, or unrelated tmux sessions

#### Scenario: Same-session send-keys resolves from tmux discovery without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents self gateway send-keys --sequence "<[Escape]>"` from inside the owning managed tmux session
- **AND WHEN** that tmux session publishes valid manifest-first discovery metadata
- **THEN** the CLI sends the control input to that session without requiring `--agent-id` or `--agent-name`

#### Scenario: Same-session notifier enable resolves from tmux discovery without explicit selectors
- **WHEN** an operator runs `houmao-mgr agents self gateway mail-notifier enable --interval-seconds 60` from inside the owning managed tmux session
- **AND WHEN** that tmux session publishes valid manifest-first discovery metadata
- **THEN** the CLI enables notifier behavior on that session without requiring `--agent-id` or `--agent-name`

#### Scenario: Outside-tmux gateway control fails without explicit selectors
- **WHEN** an operator requests an operation that requires current tmux authority without that authority or an explicit selected-agent target
- **THEN** the command fails explicitly
- **AND THEN** it does not guess a managed-agent target from cwd or ambient shell state

### Requirement: `houmao-mgr agents gateway tui` exposes raw gateway-owned TUI tracking commands
`houmao-mgr agents gateway tui` SHALL expose `state`, `history`, `watch`, and `note-prompt` over live gateway-owned TUI tracking.

#### Scenario: TUI inspection uses gateway-owned state and history
- **WHEN** a caller runs the `state`, `watch`, or `history` TUI command
- **THEN** `state` reads live gateway-owned TUI state instead of the transport-neutral summary
- **AND THEN** `watch` repeatedly reads the same state
- **AND THEN** `history` reads bounded gateway snapshots instead of the coarse managed-agent `/history`

#### Scenario: TUI prompt notes use tracking
- **WHEN** a caller runs `note-prompt`
- **THEN** the CLI sends the note to the live gateway prompt-note tracking path without creating a queued request

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
`agents gateway tui state|history|watch|note-prompt` SHALL accept explicit managed-agent targeting and the standard gateway current-session discovery.

#### Scenario: TUI current-session discovery uses the gateway targeting rules
- **WHEN** a caller omits selectors inside the owning tmux session
- **THEN** the CLI uses the same manifest-first discovery as other gateway commands

#### Scenario: TUI commands fail without a target outside tmux
- **WHEN** a caller omits selectors outside tmux
- **THEN** the CLI fails explicitly without inferring a target from cwd, gateway listener bindings, or shell state

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
Explicit pair authority for `agents gateway send-keys` and `agents single ... gateway mail-notifier` SHALL support `houmao-passive-server`. The CLI SHALL use its supported pair-authority factory and managed-agent gateway proxy instead of requiring direct listener discovery.

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
`houmao-mgr agents turn events` SHALL replay canonical semantic events and honor root print style. It SHALL support `--detail concise|detail` with `concise` as the default.

#### Scenario: Replay formats preserve canonical events
- **WHEN** a caller selects plain, JSON, or fancy output
- **THEN** plain prints human-readable summaries, JSON prints canonical semantic JSON, and fancy prints rich human-readable output
- **AND THEN** plain and fancy reuse the live bridge's headless renderer for the selected style and detail
- **AND THEN** replay does not emit raw provider stdout

#### Scenario: Replay detail controls the evidence shown
- **WHEN** a caller selects or defaults to `concise`
- **THEN** the summary leads with answer text, includes concise action requests and results, and includes provider completion or usage accounting when available

#### Scenario: Detailed replay includes canonical model fields
- **WHEN** a caller selects `--detail detail`
- **THEN** the output includes the extra structured event detail defined by the canonical headless event model

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
`houmao-mgr` SHALL expose managed-agent mailbox discovery and follow-up under `agents single ... mail` and `agents self mail`. It SHALL resolve mailbox execution from the selected managed-agent authority.

#### Scenario: Scoped mail exposes discovery and lifecycle operations
- **WHEN** a caller selects `agents single ... mail` or `agents self mail`
- **THEN** the scope exposes `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`
- **AND THEN** `resolve-live` returns machine-readable mailbox binding and live gateway discovery data

#### Scenario: Scoped selection follows the chosen identity
- **WHEN** a caller runs a scoped mail command
- **THEN** `agents single` requires `--agent-id` or `--agent-name` before `mail` and preserves that explicit target inside another managed session
- **AND THEN** `agents self` uses `HOUMAO_MANIFEST_PATH` and then `HOUMAO_AGENT_ID` for current-agent discovery
- **AND THEN** self targeting fails outside a resolvable owning session without guessing from cwd or shell state

#### Scenario: The CLI selects mailbox authority for the resolved agent
- **WHEN** a command has resolved the managed agent
- **THEN** pair-managed targets use pair-owned mail authority
- **AND THEN** local targets use verified manager-owned or gateway-backed execution when available
- **AND THEN** verified local execution does not require prompting the agent to interpret mailbox instructions
- **AND THEN** the caller does not have to discover or call a gateway endpoint

#### Scenario: TUI fallback preserves uncertainty
- **WHEN** a local live-TUI target lacks verified direct or gateway authority for an ordinary mailbox action such as `list`, `send`, `reply`, or `archive`
- **THEN** the CLI may use TUI-mediated submission but reports an non-authoritative submission result instead of claiming mailbox success
- **AND THEN** operator-origin `post` fails explicitly without verified manager-owned, pair-owned, or gateway-backed mail authority and never uses TUI submission

#### Scenario: Mailbox mutations and notifier controls require a channel
- **WHEN** a caller runs a mail lifecycle operation or notifier control
- **THEN** the command requires `--channel offline|online` and rejects missing input without inferring it from canonical mail precedence
- **AND THEN** only summary `mail status` and `resolve-live` return both channels without a selection

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
Expected operator-facing mailbox-management and gateway notifier failures SHALL produce explicit CLI errors and a non-zero exit without a Python traceback.

#### Scenario: Mailbox error formatting covers every named command
- **WHEN** an expected Click usage, manifest/runtime readiness, or gateway readiness failure reaches the root wrapper
- **THEN** offline `join`, `leave`, and `status` under `agents single ... mailbox offline`, scoped `agents self mail`, and selected-agent `gateway mail-notifier status|enable|disable` all retain non-zero exit behavior
- **AND THEN** the CLI surfaces the explicit failure reason without claiming success

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
`houmao-mgr` SHALL remove the `cao` namespace and top-level `launch`. The `server` group SHALL replace `cao` lifecycle commands, including info and shutdown. `agents launch` SHALL replace `cao launch` and the former top-level command.

#### Scenario: Repository guidance uses the replacement commands
- **WHEN** repository docs, tests, examples, or scripts reference agent launch or server lifecycle
- **THEN** they use `houmao-mgr agents launch` and `houmao-mgr server *` instead of the retired command paths

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
Active documentation under `docs/` SHALL show `houmao-mgr` and `houmao-server` for current managed-agent and pair workflows. It SHALL confine `houmao-cli` references to explicit migration, legacy, retirement, or historical guidance. It SHALL omit `houmao-mgr agents history` from supported inspection commands.

#### Scenario: Current examples omit `houmao-cli` even without a replacement
- **WHEN** active documentation describes a current workflow that lacks a native replacement
- **THEN** it does not retain `houmao-cli` as the default example

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

### Requirement: `houmao-mgr agents stop` recovers verified broken active local lifecycle authority
`houmao-mgr agents stop` SHALL recover a local tmux-backed agent whose registry record is still active after verified stale or degraded tmux authority. It SHALL re-check the registry generation and tmux authority before changing lifecycle state.

#### Scenario: Broken active authority with relaunch data becomes stopped
- **WHEN** the stored relaunch authority is readable
- **THEN** the command transitions the same generation from active to stopped, clears active liveness and gateway metadata, and preserves runtime relaunch locators
- **AND THEN** the command identifies `houmao-mgr agents relaunch` as the revival command and does not publish a new stopped generation while the old one owns the active record

#### Scenario: Broken active authority without relaunch data is retired
- **WHEN** the stored relaunch authority is unreadable
- **THEN** the command retires or removes the broken record through supported registry cleanup and reports that a fresh launch is required

#### Scenario: Stale active stop transitions the same generation to stopped
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name alice`
- **AND WHEN** registry-first local discovery resolves a fresh active tmux-backed record for `alice`
- **AND WHEN** the recorded tmux session no longer exists
- **AND WHEN** the record still has readable manifest-owned relaunch authority
- **THEN** `houmao-mgr` transitions that same registry generation to lifecycle state `stopped`
- **AND THEN** the command succeeds without a shared-registry ownership conflict
- **AND THEN** the result includes the manifest path and session root for the recovered stopped session

#### Scenario: Degraded active stop tears down broken local authority before stopped transition
- **WHEN** an operator runs `houmao-mgr agents stop --agent-id abc123`
- **AND WHEN** the resolved active tmux-backed record's tmux session exists
- **AND WHEN** the contractual primary tmux surface is missing
- **AND WHEN** the record still has readable manifest-owned relaunch authority
- **THEN** `houmao-mgr` tears down the broken Houmao-owned tmux session
- **AND THEN** it transitions that same registry generation to lifecycle state `stopped`
- **AND THEN** the command succeeds without requiring the operator to kill tmux manually

#### Scenario: Broken active stop retires unrelaunchable local authority
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name alice`
- **AND WHEN** the resolved active local tmux-backed record is stale or degraded
- **AND WHEN** the manifest or agent-definition authority needed for relaunch is unreadable
- **THEN** `houmao-mgr` retires or removes the broken active record through supported registry cleanup semantics
- **AND THEN** the command reports that the managed-agent identity cannot be relaunched from preserved local authority

### Requirement: `houmao-mgr agents stop` provides actionable recovery guidance on unexpected failures
On an unexpected failure, `houmao-mgr agents stop` SHALL identify the failing phase and known target context and report the safest supported recovery step.

#### Scenario: Stop guidance identifies the failed phase and target
- **WHEN** a normal stop cannot complete
- **THEN** the diagnostic distinguishes tmux teardown, manifest/controller reconstruction, registry lifecycle transition, or cleanup and reaping as applicable
- **AND THEN** when known, it includes `agent_name`, `agent_id`, `manifest_path`, `session_root`, and the recorded tmux session name

#### Scenario: Stop guidance gives an actionable command
- **WHEN** the CLI can construct a precise follow-up command
- **THEN** the guidance shows that exact command and prefers a dry run before destructive recovery unless the caller already requested destructive recovery
- **AND THEN** the caller receives a supported next step without needing to inspect runtime files, registry internals, or raw tmux state on their own

#### Scenario: Registry transition failure includes cleanup dry-run guidance
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name alice`
- **AND WHEN** local tmux teardown or stale-authority classification completes
- **AND WHEN** publishing the stopped shared-registry transition fails unexpectedly
- **THEN** the stop error explains that runtime authority may already be stopped while the registry may remain stale
- **AND THEN** the error includes an exact `houmao-mgr agents cleanup session ... --purge-registry --dry-run` command using `--manifest-path`, `--session-root`, `--agent-id`, or `--agent-name` according to the most precise available selector

#### Scenario: Unknown stop failure preserves artifact context
- **WHEN** an operator runs `houmao-mgr agents stop --agent-id abc123`
- **AND WHEN** an unexpected runtime-domain failure prevents completion
- **THEN** `houmao-mgr` exits non-zero without a Python traceback
- **AND THEN** the error reports what target context was known
- **AND THEN** the error includes at least one supported Houmao-native inspection, retry, cleanup, or recovery command

#### Scenario: Stop guidance does not suggest unsafe prefix-only tmux reaping
- **WHEN** `houmao-mgr agents stop` detects possible leftover tmux sessions for a managed-agent name
- **THEN** any destructive reaping guidance requires Houmao-owned authority such as matching `HOUMAO_AGENT_ID` or `HOUMAO_MANIFEST_PATH`
- **AND THEN** the guidance does not tell the operator to kill every tmux session matching only a friendly-name or `HOUMAO-` prefix

### Requirement: `houmao-mgr agents relaunch` exposes tmux-backed managed-session recovery
`houmao-mgr agents relaunch` SHALL recover tmux-backed managed sessions through explicit identity or owning-session targeting. It SHALL use manifest-first discovery and reuse the persisted session and built home instead of invoking build-time launch.

#### Scenario: Relaunch selects a path from the verified broken authority
- **WHEN** a resolved local active record has degraded or stale tmux authority
- **THEN** if the session still exists but its primary surface is missing, the CLI uses degraded-active recovery for the same logical agent
- **AND THEN** if the recorded session is gone, it revives the same agent through preserved relaunch authority when supported metadata remains
- **AND THEN** it transitions the broken record out of active state with the expected generation before publishing a new live generation

#### Scenario: Relaunch rejects missing or unsupported authority
- **WHEN** a target is not tmux-backed, has no valid manifest-owned relaunch authority, or cannot be resolved by supported selectors or current-session discovery
- **THEN** the CLI reports the failure explicitly

#### Scenario: Current-session relaunch uses tmux-local discovery
- **WHEN** an operator runs `houmao-mgr agents relaunch` from inside a tmux-backed managed session
- **THEN** `houmao-mgr` resolves that session through `HOUMAO_MANIFEST_PATH` or `HOUMAO_AGENT_ID`
- **AND THEN** it relaunches the managed agent surface without requiring an explicit selector

#### Scenario: Explicit relaunch recovers degraded active local authority
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **AND WHEN** the resolved local managed agent still has an existing tmux session
- **AND WHEN** the contractual primary tmux surface is missing from that session
- **THEN** `houmao-mgr` routes the request through degraded-active recovery
- **AND THEN** it relaunches the existing logical managed session instead of requiring a fresh launch
- **AND THEN** it does not fail with a shared-registry ownership conflict from the previous active generation

#### Scenario: Explicit relaunch revives stale active local authority
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **AND WHEN** the resolved local managed agent still claims lifecycle state `active`
- **AND WHEN** the recorded tmux session no longer exists
- **AND WHEN** supported relaunch metadata remains available
- **THEN** `houmao-mgr` routes the request through stale-active revival
- **AND THEN** it recreates live tmux-backed authority for that same logical managed agent
- **AND THEN** it does not fail with a shared-registry ownership conflict from the previous active generation

#### Scenario: Stale-active revival failure leaves stopped continuity
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **AND WHEN** stale-active recovery transitions the verified broken active record to stopped
- **AND WHEN** stopped-session revival then fails before publishing a new active generation
- **THEN** the registry record remains stopped and relaunchable when preserved authority is still valid
- **AND THEN** the operator is not left with a stale active record blocking retry

#### Scenario: Non-tmux-backed target fails clearly
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **AND WHEN** the resolved managed agent is not a tmux-backed relaunchable session
- **THEN** the command fails explicitly
- **AND THEN** it does not pretend that build-time launch or a raw CAO path is a supported replacement

### Requirement: `houmao-mgr agents relaunch` exposes relaunch chat-session selection
`houmao-mgr agents relaunch` SHALL accept `new`, `tool_last_or_new`, and `exact` for tmux-backed chat-session selection. It SHALL default to `new` and accept a provider-native chat-session ID only with `exact`.

#### Scenario: Chat-session selection preserves both forms of targeting
- **WHEN** a caller chooses a relaunch chat-session mode
- **THEN** the CLI accepts explicit `--agent-id` or `--agent-name`, or current-session targeting in the owning managed tmux session

#### Scenario: Relaunch rejects invalid selectors and unavailable conversation policy
- **WHEN** the selector is invalid, the target cannot relaunch, or its provider/backend cannot use the requested mode
- **THEN** the CLI reports a clear failure

#### Scenario: Current-session relaunch continues latest provider chat
- **WHEN** an operator runs `houmao-mgr agents relaunch --chat-session-mode tool_last_or_new` from inside a supported tmux-backed managed session
- **THEN** the command resolves the current session through tmux-local manifest discovery
- **AND THEN** it passes the latest-chat relaunch selector into the runtime relaunch primitive

#### Scenario: Explicit relaunch resumes exact provider chat
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-name reviewer --chat-session-mode exact --chat-session-id abc123`
- **THEN** the command resolves managed agent `reviewer`
- **AND THEN** it passes exact provider session id `abc123` into the runtime relaunch primitive

#### Scenario: Exact relaunch requires an id
- **WHEN** an operator runs `houmao-mgr agents relaunch --chat-session-mode exact` without `--chat-session-id`
- **THEN** the command fails validation before relaunching the managed session
- **AND THEN** it does not silently fall back to latest-chat or fresh-chat relaunch

#### Scenario: Fresh relaunch remains the default
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123` without relaunch chat-session flags
- **THEN** the command uses relaunch chat-session mode `new`
- **AND THEN** existing relaunch scripts keep their prior behavior

### Requirement: Managed-agent-targeting native CLI commands use explicit identity selectors
Selected-agent commands SHALL use one explicit agent ID or friendly name. Local gateway commands MAY instead use the group-level tmux session alias. Self commands SHALL resolve the caller's verified managed runtime.

#### Scenario: Identity selectors use authoritative identity and unique names
- **WHEN** a caller targets one managed agent
- **THEN** `--agent-id` addresses the authoritative globally unique identity
- **AND THEN** `--agent-name` succeeds only when the relevant authority can prove exactly one live agent uses that friendly name

#### Scenario: Local selector misses retain their context
- **WHEN** registry-first discovery finds no live agent with the requested friendly name and resolution later fails
- **THEN** the resulting failure retains the local friendly-name miss alongside any subsequent transport failure

#### Scenario: Friendly-name fallback preserves local evidence
- **WHEN** registry-first discovery finds no live agent with the requested friendly name and default pair fallback is unavailable
- **THEN** the CLI reports the local miss and remote lookup failure together
- **AND THEN** it suggests a correction such as `houmao-mgr agents list`, the correct friendly name, or `--agent-id`

#### Scenario: A tmux alias receives a targeted correction
- **WHEN** the supplied friendly-name selector matches a unique live local tmux or session alias but not that agent's friendly name
- **THEN** the CLI explains that `--agent-name` expects the friendly name and directs the caller to the published `agent_name` or `--agent-id`

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
`houmao-mgr agents gateway attach` SHALL default tmux-backed sessions to same-session foreground gateway execution and accept `--background` for detached execution.

#### Scenario: Foreground attachment follows the managed session topology
- **WHEN** a caller attaches without `--background`
- **THEN** a runtime-owned tmux-backed session attaches or reuses a gateway in a same-session foreground window
- **AND THEN** a pair-managed `houmao_server_rest` session uses its standard same-session auxiliary-window topology

#### Scenario: Background mode uses a detached process
- **WHEN** a caller requests `--background` for a tmux-backed managed session
- **THEN** the CLI attaches or reuses a gateway in detached background execution

#### Scenario: Foreground mode publishes the gateway window
- **WHEN** foreground tmux-window mode is active
- **THEN** `attach` and `status` report the execution mode and authoritative live gateway window index
- **AND THEN** the agent remains on window `0` and the gateway uses index `>=1`

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
`houmao-mgr admin cleanup` SHALL provide local maintenance over Houmao-owned state. Its documented tree SHALL include `registry` and `runtime sessions|builds|logs|mailbox-credentials`.

#### Scenario: Registry cleanup uses local probes unless requested otherwise
- **WHEN** a caller runs `admin cleanup registry`
- **THEN** tmux-backed records receive a local liveness probe by default, and `--no-tmux-check` opts into lease-only behavior
- **AND THEN** the documentation describes cleanup as local maintenance outside the pair-managed API

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
`houmao-mgr mailbox messages list` and `get` SHALL inspect the structure of one filesystem mailbox root and one selected address. Participant-local follow-up state SHALL use a supported scope.

#### Scenario: Structural inspection reports canonical and projection metadata
- **WHEN** a caller inspects messages for the selected address
- **THEN** the command may show message and thread identity, projection folder and path, canonical path, sender and recipient metadata, body, headers, and attachments
- **AND THEN** its output omits mutable participant-local fields such as `read`, `starred`, `archived`, and `deleted`

#### Scenario: Read state uses an actor-scoped command
- **WHEN** a caller needs participant-local read or unread state
- **THEN** the supported surface is actor-scoped mail, such as `houmao-mgr agents self mail ...`, or a future explicitly address-scoped state surface

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
Gateway commands under `agents single` SHALL accept exactly one group-level agent ID, friendly name, or supported local tmux alias. `agents self gateway` SHALL use verified current-session authority.

#### Scenario: Gateway operations share the explicit tmux selector

- **WHEN** an operator uses a gateway alias on `agents single`
- **THEN** the option is a group-level selector for local gateway commands

#### Scenario: An explicit tmux session supplies local authority

- **WHEN** the caller's enclosing tmux server does not contain the selected session
- **THEN** a unique fresh registry match resolves the peer's local owner

#### Scenario: Outside-tmux gateway status resolves by explicit tmux session selector

- **WHEN** an operator runs `houmao-mgr agents single --target-tmux-session HOUMAO-gpu-coder-1-1775467167530 gateway status`
- **THEN** the command resolves a unique fresh local registry record for that alias
- **AND THEN** it returns the selected owner's recorded or verified gateway status

#### Scenario: Gateway prompt supports the tmux-session selector across the command family

- **WHEN** an operator runs `houmao-mgr agents single --target-tmux-session HOUMAO-gpu-coder-1-1775467167530 gateway prompt --prompt hi`
- **THEN** the command submits the gateway-mediated request to that selected target

#### Scenario: Pair ports apply only to identity selectors

- **WHEN** an operator supplies `--pair-port` with a selected-agent gateway command
- **THEN** the command accepts the override only with an explicit agent ID or name
- **AND THEN** the override selects the pair authority and is distinct from the gateway listener port

#### Scenario: Port override is rejected for tmux-session targeting

- **WHEN** an operator combines a tmux alias with `--pair-port`
- **THEN** the CLI reports that pair selection requires an explicit agent ID or name

#### Scenario: Explicit pair-authority override uses the clearer flag name

- **WHEN** an operator runs `houmao-mgr agents single --agent-id abc123 gateway status --pair-port 9891`
- **THEN** the command targets the pair authority at port `9891`

### Requirement: `houmao-mgr agents interrupt` keeps TUI interrupt transport-neutral
`houmao-mgr agents interrupt` SHALL expose one transport-neutral operator contract. TUI interrupt SHALL send one best-effort `Escape` through resolved managed-agent authority. Headless interrupt SHALL use managed execution control.

#### Scenario: TUI interrupt works across tracked phases
- **WHEN** a caller interrupts a TUI-backed agent
- **THEN** the CLI dispatches without requiring raw key input
- **AND THEN** a coarse `idle` or other non-active phase alone does not veto the dispatch

#### Scenario: Idle headless interruption may be a no-op
- **WHEN** a headless managed agent has no active work
- **THEN** the managed execution interrupt command may return a no-op

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
Native `houmao-mgr agents` commands SHALL report expected local realm-controller resume or recovery failures as explicit CLI errors without Python tracebacks.

#### Scenario: Local resume failures use clean CLI errors
- **WHEN** registry-first discovery resolves a local target for `stop`, `prompt`, `interrupt`, or `relaunch` and controller resume or recovery fails with an expected runtime-domain error
- **THEN** the CLI prints a clean error
- **AND THEN** commands without a degraded-recovery contract also report stale or unusable tmux authority as a clean error

#### Scenario: Lifecycle commands attempt broken-authority recovery first
- **WHEN** `stop` or `relaunch` encounters degraded-active or stale-active authority
- **THEN** the CLI attempts the supported recovery path before reporting a contextual CLI error
- **AND THEN** a `stop` failure includes known target context and exact supported follow-up commands when available

#### Scenario: Degraded active local stop succeeds without traceback
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name alice`
- **AND WHEN** registry-first local discovery resolves managed agent `alice`
- **AND WHEN** local tmux inspection shows that the tmux session still exists but the contractual primary surface is missing
- **THEN** `houmao-mgr` uses degraded-active recovery instead of exiting on the first resume failure
- **AND THEN** the stop result is rendered without a Python traceback

#### Scenario: Stale active local stop succeeds without traceback
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name alice`
- **AND WHEN** registry-first local discovery resolves managed agent `alice`
- **AND WHEN** local tmux inspection shows that the recorded tmux session no longer exists
- **THEN** `houmao-mgr` uses stale-active recovery instead of exiting on the first resume failure
- **AND THEN** the stop result is rendered without a Python traceback

#### Scenario: Local stop recovery failure includes guidance instead of traceback
- **WHEN** an operator runs `houmao-mgr agents stop --agent-id agent-123`
- **AND WHEN** registry-first local discovery resolves that managed agent
- **AND WHEN** local stop recovery fails with an expected realm-controller runtime-domain error
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports the failure as explicit CLI error text for that managed agent
- **AND THEN** stderr includes a supported follow-up command for inspection, cleanup, retry, or recovery when one can be derived
- **AND THEN** stderr does not include a Python traceback

#### Scenario: Local prompt target runtime failure still renders as CLI error text
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id agent-123 --prompt "hello"`
- **AND WHEN** registry-first local discovery resolves that managed agent
- **AND WHEN** local controller resume fails with an expected realm-controller runtime-domain error
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports the failure as explicit CLI error text for that managed agent
- **AND THEN** stderr does not include a Python traceback

### Requirement: `houmao-mgr` headless prompt commands expose request-scoped execution override flags
`agents turn submit`, `agents gateway prompt`, and `agents prompt` SHALL accept headless request overrides `--model <name>` and `--reasoning-level <non-negative integer>`. Overrides SHALL apply to the current request.

#### Scenario: Override requests preserve inherited fields
- **WHEN** a caller provides either execution override
- **THEN** the CLI constructs `execution.model` with only supplied subfields so launch-resolved defaults can supply the remainder
- **AND THEN** `turn submit` uses the managed headless route, `gateway prompt` uses direct gateway prompt control, and plain `prompt` uses the transport-neutral route

#### Scenario: Execution flags fail when unsupported
- **WHEN** a caller supplies execution flags to `gateway prompt` or `prompt`
- **THEN** the CLI resolves the target before dispatch and rejects the flags on TUI-backed targets with a clear error

#### Scenario: Reasoning level validation permits backend-specific ranges
- **WHEN** a caller supplies `--reasoning-level`
- **THEN** the CLI rejects a negative value and does not impose a portable `1..10` upper bound

#### Scenario: Managed headless turn submit accepts both execution flags
- **WHEN** an operator runs `houmao-mgr agents turn submit --agent-id abc123 --prompt "review this" --model gpt-5.4-mini --reasoning-level 3`
- **THEN** `houmao-mgr` submits the managed headless turn successfully
- **AND THEN** the request includes `execution.model.name = "gpt-5.4-mini"` and `execution.model.reasoning.level = 3`

#### Scenario: Transport-neutral prompt forwards partial execution override for a headless target
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id abc123 --prompt "review this" --reasoning-level 12`
- **AND WHEN** the resolved managed agent is headless
- **THEN** `houmao-mgr` submits that prompt through the supported transport-neutral managed-agent path
- **AND THEN** the request includes only the partial execution override for reasoning level `12`

#### Scenario: Gateway prompt rejects execution override for a TUI target
- **WHEN** an operator runs `houmao-mgr agents gateway prompt --agent-id abc123 --prompt "review this" --model gpt-5.4-mini`
- **AND WHEN** the resolved managed agent is TUI-backed
- **THEN** `houmao-mgr` fails that command clearly
- **AND THEN** it does not silently send a TUI gateway prompt while dropping the requested model override

#### Scenario: Negative reasoning-level flag is rejected clearly
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id abc123 --prompt "review this" --reasoning-level -1`
- **THEN** `houmao-mgr` rejects that input clearly
- **AND THEN** the CLI does not construct or send an invalid request payload

### Requirement: `houmao-mgr` exposes `internals` as a top-level utility command family
`houmao-mgr` SHALL expose `internals` at its root for agent and maintainer utilities, including NetworkX-backed `graph` tooling. The family SHALL appear in root help and SHALL use the shared output engine for structured results.

#### Scenario: Internals operations stay within the utility surface
- **WHEN** the CLI registers internal utilities
- **THEN** it places the utilities under `internals` without exposing them as managed-agent lifecycle commands

#### Scenario: Root help shows internals
- **WHEN** an operator runs `houmao-mgr --help`
- **THEN** the help output includes `internals` among the supported top-level command families
- **AND THEN** the help output does not present `internals` as a replacement for `agents`, `server`, `project`, or `system-skills`

#### Scenario: Internals help shows graph tooling
- **WHEN** an operator runs `houmao-mgr internals --help`
- **THEN** the help output includes the `graph` command family
- **AND THEN** the command is described as an internal utility surface

#### Scenario: Graph command output honors print-json
- **WHEN** an operator runs an `internals graph` command with the root `--print-json` flag
- **THEN** the command emits machine-readable JSON through the shared output engine
- **AND THEN** it does not bypass the configured print style with ad hoc printing for structured payloads

### Requirement: `houmao-mgr agents mail post` defaults to operator mailbox replies
`agents single ... mail post` SHALL accept and default `--reply-policy` to `operator_mailbox`. It SHALL also accept `none` and document `operator_mailbox` as the default.

#### Scenario: Reply policy controls operator-origin message handling
- **WHEN** an operator posts a message
- **THEN** the default or explicit `operator_mailbox` permits later replies to `HOUMAO-operator@houmao.localhost`
- **AND THEN** explicit `none` creates a no-reply message and replies against that message fail explicitly

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

### Requirement: `houmao-mgr agents mail` exposes mailbox lifecycle commands
Scoped `agents single` and `agents self` mail commands SHALL provide lifecycle controls for the selected mailbox. Result reporting SHALL distinguish verified execution from non-authoritative fallback submission.

#### Scenario: Scoped mail exposes its lifecycle operations
- **WHEN** an operator opens the mail family
- **THEN** it includes `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`
- **AND THEN** `list` accepts a mailbox box and defaults to the inbox

#### Scenario: Reading and replying record only the applicable changes
- **WHEN** a caller retrieves or replies to one message
- **THEN** `peek` retrieves it without marking it read, while `read` retrieves it and marks it read
- **AND THEN** a successful `reply` marks the replied message answered

#### Scenario: Lifecycle commands update selected messages
- **WHEN** a caller changes message state
- **THEN** `mark` explicitly sets supported fields such as `read` and `answered`, `move` transfers selected messages among supported mailbox boxes, and `archive` is the shortcut for marking selected processed mail archived

#### Scenario: Lifecycle and notifier requests use an explicit channel
- **WHEN** a caller runs a mail lifecycle operation or notifier control
- **THEN** the command requires `--channel offline|online` and rejects omission without inferring from canonical mail precedence
- **AND THEN** only summary `mail status` and `resolve-live` return both channels without selection

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
Scoped `gateway mail-notifier enable` SHALL accept the mode `any_inbox` or `unread_only` and optional `--appendix-text`. Notifier `status` and `enable` results SHALL show the effective mode and `appendix_text` returned by the gateway.

#### Scenario: Notifier enable sends the selected mode and appendix
- **WHEN** a caller enables a notifier
- **THEN** the CLI sends `any_inbox` when mode is omitted and `unread_only` when requested
- **AND THEN** an omitted `--appendix-text` leaves the request field absent so the stored value remains
- **AND THEN** a non-empty appendix is sent verbatim and an explicit empty string clears the stored appendix

#### Scenario: Scoped notifier controls require an explicit channel
- **WHEN** a caller uses mail lifecycle operations or notifier controls under `agents single` or `agents self`
- **THEN** the CLI requires `--channel offline|online` and rejects omission without applying canonical mail precedence
- **AND THEN** only summary `mail status` and `resolve-live` return both channels without a selection

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

### Requirement: `houmao-mgr` root error handling does not leak uncaught maintained-command exceptions as Python tracebacks
The `houmao-mgr` root wrapper SHALL convert uncaught maintained-command exceptions into stable CLI errors with a non-zero exit and without a Python traceback. It SHALL preserve already-normalized errors.

#### Scenario: Root exception handling covers maintained command families
- **WHEN** a maintained command under `server`, `agents`, `brains`, `credentials`, `admin`, `mailbox`, `project`, or `system-skills` reports an explicit CLI error or leaks a non-Click exception
- **THEN** the wrapper keeps the explicit failure or renders a stable error for the uncaught exception
- **AND THEN** both cases exit non-zero without a traceback

#### Scenario: Project mailbox failure that reaches the root wrapper still renders without traceback

- **WHEN** an operator runs `houmao-mgr project mailbox accounts list`
- **AND WHEN** that maintained command leaks a mailbox-related exception to the top-level wrapper
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** the operator sees CLI error text instead of a Python traceback

#### Scenario: Project recipe failure that reaches the root wrapper still renders without traceback

- **WHEN** an operator runs `houmao-mgr internals native-agent recipes list`
- **AND WHEN** that maintained command leaks a malformed-preset parsing exception to the top-level wrapper
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** the operator sees CLI error text instead of a Python traceback

### Requirement: `houmao-mgr agents mail send` and `post` accept `--notify-block` and respect the houmao-notify body fence
`agents single ... mail send` and `post` SHALL support canonical `notify_block` composition through an optional `--notify-block` or a `houmao-notify` body fence. The explicit flag SHALL take precedence.

#### Scenario: Explicit notification text forms a typed envelope field
- **WHEN** the caller supplies `--notify-block <text>`
- **THEN** the CLI submits the text and `--notify-block-placement [append|prepend]` as `notify_block.text` and `notify_block.placement`, defaulting to `append`
- **AND THEN** composition synthesizes a `houmao-notify` fence in `body_markdown` at the requested placement if one is absent
- **AND THEN** the CLI does not independently extract a body fence over the explicit field

#### Scenario: A body fence follows canonical extraction rules
- **WHEN** the caller omits `--notify-block` and `--body-content` or its equivalent contains a `houmao-notify` fence
- **THEN** the CLI ignores `--notify-block-placement` and sends the body unchanged through canonical composition
- **AND THEN** the extractor takes the first matching fence and defaults placement to `append`

#### Scenario: Notification failures are clean CLI errors
- **WHEN** canonical composition reports the 512-character truncation outcome or a `verifier not yet supported` rejection
- **THEN** the CLI gives an explicit command-line error without a traceback

#### Scenario: Notification authentication remains part of programmatic composition
- **WHEN** a caller prepares a normal `send` or `post` request
- **THEN** the CLI accepts omitted `notify_auth` and treats it as no authentication metadata
- **AND THEN** callers supplying `notify_auth` use programmatic composition because the CLI has no `--notify-auth-*` flag family

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

### Requirement: Scoped online mailbox commands manage live account bindings
The maintained `agents single` and `agents self` trees SHALL expose `mailbox online status|attach|refresh|reconnect|detach`. Attach SHALL accept provider endpoint, address, login identity, and a protected credential reference. Attach SHALL accept repeatable `--trust-jmap-origin` options. Account selection and replacement intent SHALL be explicit when needed. Mutations SHALL preserve agent ID, body conversation, and offline binding.

#### Scenario: Operator attaches a hub-provisioned account
- **WHEN** an operator runs scoped `mailbox online attach` with valid Stalwart account inputs
- **THEN** the command reports the committed binding ID/revision and canonical mail identity
- **AND THEN** it does not require management credentials or a body relaunch

#### Scenario: Refresh rejects another account
- **WHEN** scoped `mailbox online refresh` resolves credentials for an account different from the current binding
- **THEN** the command returns an explicit identity mismatch and preserves the current binding

#### Scenario: Detached provider mail is retained
- **WHEN** an operator runs scoped `mailbox online detach`
- **THEN** only the online binding is removed and provider mail remains intact

#### Scenario: The operator opts into a selected intranet origin
- **WHEN** an authorized caller passes one or more `--trust-jmap-origin` values on scoped `mailbox online attach`
- **THEN** the command submits each exact origin with the authorized attach request
- **AND THEN** scoped `mailbox online status` reports the configured origin approvals and applicable plaintext warning

### Requirement: Native mailbox listing is paged and metadata-only
Scoped `mail list --channel offline|online` SHALL use a finite default `--limit`, enforce a maximum, accept `--cursor`, and return one metadata page with continuation and clearly scoped counts. It SHALL not fetch subsequent pages automatically. The removed `--include-body` flag SHALL fail clearly and point to peek/read.

#### Scenario: Operator continues an online metadata page
- **WHEN** a caller supplies the previous response's cursor with the same channel and filters
- **THEN** the command returns one bounded continued page without body retrieval

#### Scenario: Removed content-list flag is used
- **WHEN** a caller supplies `--include-body` to list
- **THEN** argument validation rejects it before mailbox I/O

### Requirement: Online management reports committed and uncertain outcomes safely
CLI output SHALL distinguish validated activation, stale-revision conflict, rejected credentials, endpoint failure, an unapproved or changed JMAP origin, incomplete account readiness, committed binding with projection failure, and uncertain in-flight mutation outcomes. Status SHALL expose safe binding/sync health rather than credential bytes, authorization headers, or raw provider exception dumps.

#### Scenario: Projection fails after activation
- **WHEN** online binding activation commits but a registry projection cannot be refreshed
- **THEN** the result identifies the committed revision and reconciliation need
- **AND THEN** it does not falsely claim that attachment was rolled back

#### Scenario: The account needs operator preparation
- **WHEN** the provider rejects the sending identity or reports a missing required mailbox role or permission
- **THEN** the CLI reports the specific readiness problem, gives a remediation, and exits nonzero

#### Scenario: A JMAP endpoint needs explicit approval
- **WHEN** attachment rejects an unapproved origin
- **THEN** the CLI reports the safe origin and the required approval or HTTPS configuration
- **AND THEN** it exits nonzero without displaying credentials or raw provider responses

### Requirement: Self-status commands observe established current-session authority
The manager SHALL obtain agent details for `agents self state` and `agents self mail status` from the verified manifest. It SHALL observe state through its runtime bindings without reading launch definitions or writing registry, gateway, provider, or tmux state. Mailbox status SHALL retain existing signed gateway and local owner access rules.

#### Scenario: A DSH workspace-restricted process reads its own state
- **WHEN** an owned DSH headless session runs `houmao-mgr agents self state` with `workspace-write` and the registry outside the workspace
- **THEN** the command reports the current managed session's observed state
- **AND THEN** the query needs no write permission to the shared registry

#### Scenario: A DSH workspace-restricted process reads its mailbox status
- **WHEN** the current DSH session runs `houmao-mgr agents self mail status` from that sandbox
- **THEN** the command reports the configured channels and their availability using the established authorization
- **AND THEN** resolving the session does not publish a registry record or create gateway capability files

#### Scenario: Self status is requested with invalid authority
- **WHEN** current-session discovery cannot verify a matching managed manifest or current identity
- **THEN** the command reports the resolution error without creating or reviving a session or retrying with broader authority

#### Scenario: The gateway is detached from a live current session
- **WHEN** an authorized managed session requests mailbox status and no live gateway is attached
- **THEN** the manager uses the supported local status source and identifies unavailable channels
- **AND THEN** the query does not attach a gateway

#### Scenario: A manifest is valid and its live observer is unavailable
- **WHEN** self state can verify the session and lacks fresh runtime evidence for an observation
- **THEN** the result preserves the manifest-backed identity and reports the observation's actual availability

### Requirement: The scoped gateway CLI requests a Web entry URL

`houmao-mgr agents single --agent-id <id> gateway web-entry` SHALL use the live owner-local gateway. It SHALL request a ticket unsigned in verified open mode or use an enrolled signer authorized for `web.enter` in keyed mode. The command SHALL return `url` and `expires_at_utc` without following the URL. Help SHALL describe it as a bearer secret.

#### Scenario: An operator requests an entry URL

- **WHEN** the command targets a live supported managed Web agent in keyed mode with an available signer authorized for `web.enter`
- **THEN** the command prints the gateway ticket URL and its expiry
- **AND THEN** its output contains no native launch token, browser cookie, or private bootstrap path

#### Scenario: Gateway entry authority is unavailable

- **WHEN** the selected gateway is detached, its policy is unavailable, the signer is unavailable, its proof is rejected, or it lacks permission for the selected target, or the target requires an unsupported proxy or executor route
- **THEN** the command returns actionable owner-local guidance
- **AND THEN** it performs no unsigned retry, automatic attach, or native credential fallback

#### Scenario: An operator requests a link on an open gateway

- **WHEN** the selected live owner-local Web gateway reports `admin_mode: open` for the current execution
- **THEN** the command requests and prints the one-time link and expiry without requiring a signer
- **AND THEN** the gateway independently checks the live roster and `web.enter` permission before issuance

#### Scenario: Enrollment races the unsigned CLI request

- **WHEN** the roster gains a key after the command reads open policy and before ticket issuance
- **THEN** the command surfaces the refusal and ends the attempt

### Requirement: Scoped mail creation commands report a write receipt

Scoped `mail send`, `reply`, and `post` SHALL return an authoritative CLI version-1 receipt for each verified write. It SHALL include the opaque `message_ref`, the binding that owns it, and the actual envelope fields. It SHALL omit the nested message and its contents.

#### Scenario: A gateway-backed send reports confirmation

- **WHEN** a scoped send returns a confirmed action response through the pair API or the current gateway
- **THEN** the receipt reports `operation: send`, `status: verified`, `authoritative: true`, and `execution_path: gateway_backed`
- **AND THEN** the CLI exposes `schema_version`, `channel`, `binding_id`, `transport`, `principal_id`, and `address` as top-level fields
- **AND THEN** it exposes the returned `sender_address`, `to`, `cc`, `subject`, `created_at_utc`, and exact `message_ref` as top-level fields

#### Scenario: A manager-direct send uses the same contract

- **WHEN** a manager-direct send succeeds through the selected mailbox binding
- **THEN** the receipt reports `execution_path: manager_direct` and the same verified fields as a gateway-backed send

#### Scenario: Reply distinguishes the new message and its parent

- **WHEN** a scoped reply creates a message
- **THEN** the receipt exposes the replying agent's binding and the returned envelope of the new reply
- **AND THEN** it supplies the input reference as `parent_message_ref` and the new reference as `message_ref`

#### Scenario: Operator post identifies the target binding

- **WHEN** a supported operator post creates a message
- **THEN** the receipt identifies the selected recipient's mailbox through `principal_id`, `address`, `channel`, and `binding_id`
- **AND THEN** it identifies the operator separately through `sender_address`

#### Scenario: Text and JSON give the same confirmation

- **WHEN** a caller selects plain, fancy, or JSON output for a send, reply, or post
- **THEN** that mode displays the same receipt fields and values, including actual recipient addresses and the entire reference
- **AND THEN** the command performs one write without a detail lookup to render that result

### Requirement: Scoped mail receipts preserve submission and confirmation evidence

A TUI-mediated send or reply SHALL report its request lifecycle status and request ID with `authoritative: false`. Only a verified write SHALL expose a confirmed `message_ref`. Each invocation SHALL dispatch at most one write and preserve the available evidence when the outcome is unresolved.

#### Scenario: A TUI submission has only preview evidence

- **WHEN** the TUI reports a prompt submission and emits text that resembles a successful mail result
- **THEN** the receipt reports `status: submitted`, `execution_path: tui_submission`, and the request ID
- **AND THEN** the receipt omits a confirmed reference and nested preview content
- **AND THEN** it retains the original channel and binding and directs the caller to check the sent box when authoritative lookup is available

#### Scenario: TUI reply has only the parent reference

- **WHEN** a scoped reply produces a TUI submission-only result
- **THEN** it includes the request ID and input `parent_message_ref`
- **AND THEN** it omits any unverified new reference, recipients, and subject

#### Scenario: Operator post requires verified write authority

- **WHEN** operator post would require submitting a mail request through the target TUI
- **THEN** it fails with the existing authority error and performs no TUI submission

#### Scenario: A TUI request reports an admission or execution problem

- **WHEN** the underlying TUI request reports rejection, busy, interruption, or an error
- **THEN** the receipt retains that status without claiming a verified write or a queued delivery

#### Scenario: Verification fails after a write may have committed

- **WHEN** a mail write reports a transport error with uncertainty or evidence of a prior commit
- **THEN** the CLI preserves the outcome and available reconciliation identifiers in its error
- **AND THEN** the invocation concludes without a second dispatch

### Requirement: A mail receipt supports read-only inspection

The verified receipt's `message_ref` SHALL identify the created message for authorized `mail peek` on the original channel and binding. Peeking SHALL preserve mailbox state.

#### Scenario: Read-only details follow a single send

- **WHEN** the sender peeks using the receipt's reference and original channel and binding
- **THEN** the CLI returns the selected sent message details
- **AND THEN** the message state stays unchanged and the recipient still has one copy from that send

#### Scenario: Reply and post use the binding that owns the receipt

- **WHEN** a caller needs the details of a verified reply or operator post
- **THEN** the reply reference resolves through the replying agent's binding
- **AND THEN** the post reference resolves through the selected recipient's binding, including if the message has since moved to archive

#### Scenario: A binding changes before the follow-up

- **WHEN** a caller uses a receipt reference against another agent, channel, or binding
- **THEN** the scoped lookup rejects the request before returning message content

### Requirement: Memo writes report a compact receipt

Scoped `memory memo set` and `append` SHALL report `success`, the memo write action, and `memo_file` in each output mode. `memo show` SHALL provide the current contents.

#### Scenario: Replacing or appending a memo produces one receipt

- **WHEN** the selected memo is successfully replaced or appended through a scoped command
- **THEN** it reports `success: true`, action `write_memo` or `append_memo`, and the resolved memo path
- **AND THEN** the result contains no memo text

#### Scenario: Inspecting a memo after appending preserves its contents

- **WHEN** a caller runs `memo show` after one successful append
- **THEN** the result contains the original memo followed by one copy of the addition

### Requirement: Reminder updates acknowledge the completed write

Scoped `gateway reminders set` SHALL report `status: updated`, `reminder_id`, `ranking`, `paused`, and `next_due_at_utc` from the accepted update in each output mode. The command SHALL obtain this receipt without a later read of the reminder set.

#### Scenario: A reminder update succeeds when a later read would fail

- **WHEN** the gateway accepts an update and the live reminder set is unavailable afterward
- **THEN** the command emits its receipt and exits successfully
- **AND THEN** the receipt carries the saved due time and omits reminder-set fields and prompt payloads

#### Scenario: The caller inspects the updated reminder

- **WHEN** a caller needs the reminder definition or set-wide selection information
- **THEN** the caller can use `reminders get` for the selected reminder or `reminders list` for the set

### Requirement: Native browser opening reports a serializable outcome

The `agents single ... open-browser` command SHALL serialize a successful owner-local browser action as `status`, `action`, and `detail` in every output mode.

#### Scenario: JSON output succeeds after one browser dispatch

- **WHEN** a caller selects JSON and an eligible Kimi Web owner opens the browser
- **THEN** the command opens the browser once and returns `status: ok` and `action: open_browser` with a short detail
- **AND THEN** the result contains no private URL, credentials, or bootstrap path

#### Scenario: A stale browser owner is rejected

- **WHEN** the selected browser owner fails ownership verification
- **THEN** the command exits nonzero without opening a browser

### Requirement: Gateway prompt reports admission and handoff in every output mode

Scoped `gateway prompt` SHALL return the same admission and handoff evidence in plain, fancy, and JSON output. It SHALL report `status`, `action`, `admission_policy`, `sent`, and `detail` and expose `operation_id`, `outcome`, and `native_prompt_id` when present in the gateway response. A structured gateway refusal SHALL exit nonzero.

#### Scenario: A live gateway refusal retains structured diagnostics

- **WHEN** the gateway refuses because the target is not ready, busy, unavailable, or unsupported
- **THEN** the command reports the gateway refusal as a structured JSON error and exits nonzero

#### Scenario: Gateway handoff prints the available evidence

- **WHEN** a gateway reports successful handoff
- **THEN** the command exits successfully and displays `sent: true`, the selected policy, and any reported IDs and outcome

#### Scenario: Accepted queueing stays distinct from handoff

- **WHEN** a gateway reports `outcome: queued` with `sent: false`
- **THEN** the command exits successfully and displays both values and the operation ID
- **AND THEN** it exposes a native prompt ID when supplied and performs no additional submission

#### Scenario: A named policy drives admission

- **WHEN** a caller submits a prompt through `agents single` or `agents self` using `--admission-policy`
- **THEN** the command forwards the selected policy and reports it in the result
- **AND THEN** omitting the option uses `ready-only`
