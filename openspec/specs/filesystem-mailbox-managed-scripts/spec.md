## Purpose
Define the validation, dependency, and stable CLI contract for runtime-managed Python helpers published under filesystem mailbox `rules/scripts/`.

## Requirements

### Requirement: Python managed mailbox helpers publish an explicit dependency manifest for their validation stack
The filesystem mailbox transport SHALL publish the Python dependency manifest for mailbox-managed helper scripts under `rules/scripts/requirements.txt`.

When a projected Python managed mailbox helper uses `pydantic` for request validation, that dependency manifest SHALL declare a `pydantic` requirement using a minimum-version specifier rather than an exact or upper-bounded pin.

The dependency manifest SHALL stay aligned with the imports used by the projected Python helper set so operators and agents can determine the exact Python dependencies required to invoke those helpers safely.

#### Scenario: Bootstrap publishes the pydantic dependency for Python mailbox helpers
- **WHEN** the runtime initializes or refreshes a filesystem mailbox root whose managed Python mailbox helpers validate payloads with `pydantic`
- **THEN** the shared mailbox `rules/scripts/requirements.txt` file includes a `pydantic>=...` dependency entry
- **AND THEN** the managed helper asset set is published together with that dependency manifest

#### Scenario: Managed helper dependency manifest matches helper imports
- **WHEN** an operator or agent inspects the managed mailbox helper dependency manifest before invoking a Python helper
- **THEN** the manifest reflects the Python packages actually required by the projected helper set
- **AND THEN** the system does not omit a required validation dependency from that manifest

#### Scenario: Dependency manifest does not use an exact or upper-bounded pin for pydantic
- **WHEN** the projected Python helper set requires `pydantic` in `rules/scripts/requirements.txt`
- **THEN** that manifest expresses the dependency as a minimum-version requirement
- **AND THEN** the manifest does not constrain `pydantic` with an exact `==` pin or an upper-bound range

### Requirement: Managed mailbox helpers validate payloads through strict shared schemas before mutation
Python managed mailbox helpers under `rules/scripts/` SHALL validate request payloads through strict shared schemas before performing SQLite or filesystem mutations.

At minimum, this requirement applies to delivery, mailbox-state mutation, repair, mailbox registration, and mailbox deregistration flows.

Those schemas SHALL validate constrained scalar fields such as mailbox addresses, canonical message ids, and UTC timestamps, and SHALL also validate nested structured payloads such as principals and attachments when those payloads are present.

If validation fails, the helper SHALL emit one structured JSON error result and SHALL NOT partially mutate mailbox state, mailbox artifacts, or canonical message files.

#### Scenario: Malformed register payload is rejected before mutation
- **WHEN** an operator or agent invokes `register_mailbox.py` with a payload whose required fields are missing or whose field types are invalid
- **THEN** the helper rejects the payload before creating, renaming, or deleting mailbox artifacts
- **AND THEN** the helper emits one JSON error result describing the validation failure

#### Scenario: Nested delivery payload validation fails with an explicit field-aware error
- **WHEN** an operator or agent invokes `deliver_message.py` with a delivery payload containing an invalid nested recipient or attachment field
- **THEN** the helper rejects the payload before moving the staged message into canonical storage or updating `index.sqlite`
- **AND THEN** the emitted JSON error identifies the failing field path or nested payload location explicitly

### Requirement: Managed mailbox helper CLI surfaces remain stable while schema validation is simplified
Each Python managed mailbox helper SHALL preserve the existing invocation pattern of `--mailbox-root` plus `--payload-file` and SHALL emit exactly one JSON object to stdout for both success and failure outcomes.

Simplifying helper implementation with shared schema-backed parsing SHALL NOT require callers to adopt a different script name, different flags, or an interactive prompt flow.

#### Scenario: Valid delivery request still uses the existing script contract
- **WHEN** an operator or agent invokes `deliver_message.py` with a valid payload file and mailbox root
- **THEN** the helper accepts the existing `--mailbox-root` and `--payload-file` flags
- **AND THEN** the helper emits one JSON success result object to stdout after the managed delivery completes

#### Scenario: Validation failure still returns one JSON object to stdout
- **WHEN** an operator or agent invokes any Python managed mailbox helper with an invalid payload file that fails schema validation
- **THEN** the helper emits exactly one JSON object to stdout describing the failure
- **AND THEN** the helper does not emit a second result object or require a different invocation contract for validation errors

### Requirement: Managed mailbox helpers update shared catalog state and mailbox-local state consistently
Python managed mailbox helpers under `rules/scripts/` SHALL keep shared mailbox-root catalog state and mailbox-local mailbox-view state consistent during delivery, mailbox-state mutation, and repair.

Delivery helpers SHALL:

- update shared-root structural mailbox catalog data,
- initialize sender mailbox-local state deterministically,
- initialize recipient mailbox-local state deterministically.

Those mailbox-local writes SHALL use mailbox-scoped identities keyed by `message_id`, and any mailbox-local thread summary caches maintained by the helpers SHALL be keyed by `thread_id`.

Mailbox-state update helpers SHALL mutate the addressed mailbox's local mailbox-state database rather than requiring shared-root aggregate recipient-state tables to remain authoritative.

Repair helpers SHALL rebuild shared-root structural catalog state and mailbox-local mailbox-view state through their respective recovery paths without inventing aggregate recipient-status mirrors.

When repair rebuilds mailbox-local summary caches, it SHALL derive unread thread counts from that mailbox's local message-state rows rather than carrying forward shared-root `thread_summaries.unread_count` as authoritative state.

#### Scenario: Delivery initializes sender and recipient local mailbox state
- **WHEN** an operator or agent invokes `deliver_message.py` successfully for one sender and one or more recipients
- **THEN** the helper updates the shared mailbox-root structural catalog needed for canonical messages and projections
- **AND THEN** it initializes the sender and recipient mailbox-local state records with deterministic defaults in their respective mailbox-local SQLite databases

#### Scenario: Mailbox-state helper updates one addressed mailbox locally
- **WHEN** an operator or agent invokes `update_mailbox_state.py` to mark a message read for one mailbox address
- **THEN** the helper updates that mailbox address's local mailbox-state SQLite data
- **AND THEN** the helper does not depend on a shared aggregate recipient-state mirror to make that mutation authoritative

#### Scenario: Repair rebuilds local mailbox state when only structural mailbox data survives
- **WHEN** repair finds canonical message files and mailbox projections but one mailbox-local SQLite database is missing or unreadable
- **THEN** the repair flow can recreate deterministic local mailbox state for that mailbox from the available structural mailbox artifacts
- **AND THEN** the rebuilt mailbox-local state does not require inventing a shared aggregate read-state table
- **AND THEN** any rebuilt mailbox-local unread thread summaries are derived from local mailbox state rather than from shared-root unread counters
