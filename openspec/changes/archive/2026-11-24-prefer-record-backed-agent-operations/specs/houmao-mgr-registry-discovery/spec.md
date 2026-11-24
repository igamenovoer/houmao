# Spec Delta

## ADDED Requirements

### Requirement: Scoped manager reads select saved authority before live control

`houmao-mgr` SHALL resolve an exact agent ID or unique name in the selected registry scope before requesting any live observation. It SHALL use authorized registry fields and verified manifest fields for recorded facts. Authoritative local reads SHALL check that the selected record and manifest agree on identity, generation, and execution ownership.

#### Scenario: Selected record answers a query inside another agent's session

- **WHEN** an authorized caller reads recorded metadata for a peer from inside a different managed session
- **THEN** Houmao returns the selected peer's metadata without querying either tmux server to resolve the peer
- **AND THEN** the read leaves runtime state, registry publication, and tmux environment unchanged

#### Scenario: Manifest authority has changed

- **WHEN** an operation requires current manifest authority and the recorded owner, identity, or generation disagrees with the manifest
- **THEN** the operation reports the mismatch and withholds manifest-backed results or actions
- **AND THEN** the command preserves the selected identity and does not fall through to an ambient session, another owner, or the default server

### Requirement: Scoped mail discovery preserves contact without terminal access

An explicit `mail resolve-live` request SHALL resolve the selected agent's contact from a verified manifest or its visible registry projection. The response SHALL identify published-only contact and its unverified availability. Gateway availability SHALL require current, verified endpoint evidence for the selected owner and generation. These reads SHALL use no peer tmux commands.

#### Scenario: Healthy peer uses a separate inaccessible tmux socket

- **WHEN** the selected peer's current manifest and offline registration can be read but the caller cannot access the peer's terminal socket
- **THEN** the command returns the peer's configured mailbox address, channel, and binding scope
- **AND THEN** the command reports verified gateway data only if a matching live gateway is available

#### Scenario: Known stopped peer has published contact

- **WHEN** a visible known agent retains a published mailbox address and current manifest-backed mail availability cannot be checked
- **THEN** the command returns the redacted published mailbox summary with its source and unverified availability
- **AND THEN** the result contains no live gateway claim, private runtime access, or authority to read or send from the peer's mailbox

#### Scenario: Detached recipient gateway does not gate mail delivery

- **WHEN** a verified sender submits mail through its own binding to a recipient registered in the selected offline mail authority
- **AND WHEN** the recipient has no gateway or reachable terminal
- **THEN** the mail authority processes the message through the explicit offline channel and reports the delivery result independently of recipient readiness

### Requirement: Gateway status and saved turn reads use their recorded authority

Authorized `gateway status` SHALL use the selected manifest and persisted status. Attached status requires the current-instance record and live endpoint to agree on the selected owner and generation. Authorized headless `turn status`, `events`, `stdout`, and `stderr` SHALL read the selected runtime's confined turn artifacts. These reads SHALL avoid controller construction and tmux probes.

#### Scenario: A saved headless turn remains readable

- **WHEN** authorized turn artifacts remain available under the selected runtime's verified manifest but its terminal is unavailable
- **THEN** the command returns the requested saved turn status, event stream, or output for the selected turn
- **AND THEN** a terminal readiness check is unnecessary for the read

#### Scenario: Gateway status uses its own instance evidence

- **WHEN** an authorized caller requests gateway status and the peer socket cannot be opened
- **THEN** a detached gateway reports its recorded detached status
- **AND THEN** an attached gateway requires its own current instance and endpoint evidence to report verified live status

## MODIFIED Requirements

### Requirement: Gateway tmux-session selectors resolve through fresh registry tmux aliases

`houmao-mgr agents single --target-tmux-session <tmux-session-name> gateway ...` SHALL match the exact name against fresh shared-registry terminal metadata. A unique match SHALL select that owner and its recorded socket before any terminal operation. The alias SHALL be mutually exclusive with agent selectors and pair selection.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

If no fresh record matches, the lookup SHALL report that the tmux-session selector could not be resolved through the shared registry. If more than one fresh record matches, the command SHALL fail explicitly and SHALL surface enough identity metadata for the operator to disambiguate the target.

This tmux-session alias path SHALL remain local registry-backed discovery only and SHALL NOT redefine tmux session names as remote pair-managed agent identifiers.

#### Scenario: Gateway CLI resolves a managed agent by exact tmux session alias

- **WHEN** an operator runs `houmao-mgr agents single --target-tmux-session HOUMAO-gpu-coder-1-1775467167530 gateway status`
- **AND WHEN** exactly one fresh shared-registry record has `terminal.session_name = "HOUMAO-gpu-coder-1-1775467167530"`
- **THEN** the system resolves that record as the local managed-agent target
- **AND THEN** the operator does not need to rediscover the friendly `agent_name` or authoritative `agent_id` first

#### Scenario: Ambiguous tmux session alias lookup fails closed

- **WHEN** an operator runs `houmao-mgr agents single --target-tmux-session hm-gateway-demo gateway status`
- **AND WHEN** more than one fresh shared-registry record matches that tmux session alias
- **THEN** the command fails that resolution explicitly
- **AND THEN** the error surfaces candidate `agent_id`, `agent_name`, and `terminal.session_name` values rather than silently choosing one

#### Scenario: Gateway lookup succeeds without the ambient socket

- **WHEN** an operator requests gateway status by an exact unique registry alias while inside a different tmux server
- **THEN** the manager reads the selected owner's gateway status without checking the caller's tmux server
