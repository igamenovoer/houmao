# CCCC Chat Delta

## ADDED Requirements

### Requirement: Agents Can Peek at Staged CCCC Chat

The selected CCCC gateway instance SHALL expose a read-only peek of the bounded next eligible pop selection. Peek SHALL return the original sender, timestamp, mode, text, and scoped reply handle in delivery order. The gateway SHALL indicate when additional messages are queued or a timed batch is still open.

#### Scenario: An Active Agent Inspects Queued Replies

- **WHEN** an authorized agent peeks while it is still executing a turn
- **THEN** the gateway returns the messages eligible for the next pop with their batch boundaries and an opaque selection token
- **AND THEN** peek leaves those deliveries eligible for a later claim

#### Scenario: More Messages Arrive During a Wait

- **WHEN** the agent asks peek to wait for a minimum number of eligible messages within a finite deadline
- **THEN** the gateway returns once that count is available or the deadline expires
- **AND THEN** an expired wait returns the available selection or an explicit empty result
- **AND THEN** the received messages retain their provider delivery order and original timestamps

#### Scenario: A Timed Batch Is Still Collecting Messages

- **WHEN** the gateway has staged messages in a timed batch whose boundary has yet to close
- **THEN** peek reports the open batch and includes only sealed batches in the pop selection
- **AND THEN** the ordinary quiet and maximum wait deadlines still determine when that batch seals

#### Scenario: An Intake Generation Retires During a Wait

- **WHEN** the gateway revokes or replaces the receiver lease while a peek is waiting
- **THEN** the wait ends with a typed stale or unavailable result within the request deadline

### Requirement: The Gateway Selects Each Chat Pop Batch

A pop SHALL name the snapshot returned by peek and a caller operation ID. The gateway SHALL select a count- and byte-bounded FIFO prefix of whole sealed batches. A successful pop SHALL return the exact selection as one tool result in the current turn.

#### Scenario: An Agent Pops Multiple ASAP Messages

- **WHEN** two single-message ASAP batches are queued and fit within the selected gateway limits
- **THEN** one pop can return both messages as one ordered tool result
- **AND THEN** each message retains its own handle for exact-parent reply

#### Scenario: A Pull or Timed Push Batch Is at the Head

- **WHEN** the gateway selects a sealed batch formed by a scheduled pull or timed push
- **THEN** that entire batch appears in its original order
- **AND THEN** any additional batches in the same result keep their own boundaries

#### Scenario: The Agent Sees a Later Message It Wants

- **WHEN** an agent requests pop after seeing a relevant message behind an earlier message in the peek selection
- **THEN** the gateway includes the preceding eligible batches in FIFO order within its limits
- **AND THEN** the caller can choose when to pop under the gateway-selected bounds

#### Scenario: The First Complete Batch Exceeds the Tool Result Budget

- **WHEN** the oldest batch cannot fit in a complete bounded pop result
- **THEN** the gateway returns a typed content-limit error and leaves the batch eligible for ordinary delivery

### Requirement: Pop and Automatic Delivery Share a Claim

The gateway SHALL serialize a pop and an automatic prompt claim for the same queued attempts. A fresh pop SHALL validate the exact selection at the current queue head and receiver generation. The gateway SHALL exclude attempts reserved for a tool read from automatic prompt delivery.

#### Scenario: Pop Wins the Claim During an Active Turn

- **WHEN** a valid pop claims the selected head before automatic delivery starts
- **THEN** the agent receives the claimed messages in its tool result
- **AND THEN** ordinary delivery proceeds from the next eligible work when the agent becomes ready

#### Scenario: Automatic Delivery Wins After the Agent Yields

- **WHEN** the agent yields and ordinary dispatch claims the head before an outstanding peek selection is popped
- **THEN** the configured delivery policy delivers that batch through an ordinary prompt
- **AND THEN** the stale pop returns a conflict before reading a substitute batch

#### Scenario: A New Message Appends Behind a Peeked Selection

- **WHEN** an offer is queued behind the unchanged prefix identified by a peek token
- **THEN** a pop using that token takes only the original selection

#### Scenario: A Pop Uses a Selection From a Retired Gateway Generation

- **WHEN** a new pop references a peek token issued under a different gateway run or receiver lease
- **THEN** the gateway returns a typed stale-selection conflict

### Requirement: Gateway Tool Reads Have Exact Reconciliation

The gateway SHALL allow a caller to recover a recorded pop by operation ID and acknowledge the corresponding read receipt. An acknowledged gateway tool read SHALL have a distinct delivery outcome from a confirmed prompt handoff. The reported receipt SHALL refer to the attempts selected by that pop.

#### Scenario: A Pop Response Is Lost

- **WHEN** the caller loses the pop response after its read claim commits
- **THEN** retrying the same operation ID and snapshot or looking up the operation returns the recorded selection and receipt
- **AND THEN** the retry or lookup consumes no additional queued messages

#### Scenario: The Agent Acknowledges the Tool Result

- **WHEN** an authorized agent presents a valid read receipt through the selected binding
- **THEN** CCCC records an acknowledged tool read for the exact claimed attempts
- **AND THEN** repeating the acknowledgment returns the original decision

#### Scenario: The Gateway Is Reattached Before Receipt Recovery

- **WHEN** an authorized caller looks up a recorded pop or acknowledges its receipt after replacing the gateway run for the same binding
- **THEN** the result resolves the original read claim under that binding
- **AND THEN** any reply handles returned by the replacement are scoped to its current run

### Requirement: Queue Access Uses the Selected Plugin Authority

Gateway queue operations SHALL use distinct declared read and consuming actions on the selected CCCC plugin instance. Queue access SHALL require negotiated provider support for gateway tool-read claims. Queue results SHALL preserve ordinary request attribution and expose only bounded agent-facing data.

#### Scenario: A Caller Has Peek Permission Only

- **WHEN** a caller authorized to view the queue attempts to pop without the consuming action
- **THEN** the gateway denies the pop before claiming any attempt

#### Scenario: An Older Receiver Provides Ordinary Chat

- **WHEN** the selected receiver supports ordinary delivery and lacks the gateway tool-read capability
- **THEN** capabilities report queue access unavailable and its routes return a typed unsupported result
- **AND THEN** the selected ordinary delivery policy continues to operate

#### Scenario: A Queued Message Resembles a Control Command

- **WHEN** peek or pop returns message text that resembles a privileged gateway instruction
- **THEN** the tool result presents it as CCCC request content from its recorded sender
- **AND THEN** the response uses scoped handles and excludes credentials and internal routing identifiers

## MODIFIED Requirements

### Requirement: Scheduled Pull Defines One Batch per Snapshot

In gateway pull mode, each scheduled pull with staging capacity SHALL select one bounded CCCC snapshot. Each non-empty result SHALL define exactly one delivery batch. The gateway SHALL dispatch a batch still eligible for automatic delivery when the current body can receive an ordinary prompt.

#### Scenario: A Scheduled Pull Finds Several Messages

- **WHEN** a scheduled pull returns several pending messages at its snapshot boundary
- **THEN** the gateway prepares one notification containing the complete ordered result
- **AND THEN** each later pull defines its own batch regardless of how close together the pulls occur

#### Scenario: A Scheduled Pull Finds No Messages

- **WHEN** a scheduled pull returns an empty snapshot
- **THEN** the gateway sends no prompt for that pull
- **AND THEN** a later arrival is eligible at the next scheduled pull with available capacity

#### Scenario: Pull Runs During a Busy Turn

- **WHEN** a pull returns pending messages while the body is executing a turn
- **THEN** the batch keeps its original membership and is available to pop or wait for readiness
- **AND THEN** the gateway dispatches remaining waiting batches in order

### Requirement: Push ASAP Delivers Individual Messages in Order

With push set to `asap`, each newly staged message SHALL form one single-message batch. The gateway SHALL promptly deliver the oldest batch eligible for automatic delivery when the current body can receive ordinary input. Messages arriving during an active turn SHALL wait in CCCC delivery order.

#### Scenario: A Push Arrives While the Body Is Idle

- **WHEN** an offer reaches a ready body with no earlier message waiting
- **THEN** the gateway hands it off as one ordinary prompt without a batching delay

#### Scenario: More Push Messages Arrive While the Body Is Busy

- **WHEN** subsequent messages arrive during an active turn
- **THEN** those messages wait in CCCC delivery order and are eligible for pop
- **AND THEN** the gateway hands off the remaining messages individually in CCCC delivery order as the body becomes ready

### Requirement: Push Batching Uses Quiet and Maximum Wait Deadlines

With push set to `batch`, the first staged message SHALL start a batch. The batch SHALL close at the earlier of the quiet interval after the last newly staged message and the maximum wait after the first. A closed batch SHALL be eligible for pop. A closed unclaimed batch SHALL wait for ordinary readiness before automatic dispatch.

#### Scenario: A Short Burst Ends Before the Maximum Wait

- **WHEN** messages arrive before the open batch's deadline and then no new message arrives for the configured quiet interval
- **THEN** those messages appear together in one batch that closes when the quiet interval expires

#### Scenario: A Continuous Burst Reaches the Maximum Wait

- **WHEN** new messages keep arriving before the quiet interval expires
- **THEN** the batch closes at the maximum wait measured from its first arrival
- **AND THEN** an offer arriving at or after that deadline belongs to a later batch

#### Scenario: An Offer Arrives When the Quiet Deadline Is Due

- **WHEN** a new offer arrives exactly at the open batch's quiet deadline
- **THEN** the gateway closes the existing batch first and admits the offer to a new batch
- **AND THEN** repeated offers for the same staged message do not advance either deadline

#### Scenario: A Timed Batch Closes During a Busy Turn

- **WHEN** the batch reaches its deadline while the body cannot receive a prompt
- **THEN** the closed batch keeps its membership and waits for pop or ordinary readiness
- **AND THEN** later arrivals form later batches and the gateway hands off the remaining closed batches in order
