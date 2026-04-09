## ADDED Requirements

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
