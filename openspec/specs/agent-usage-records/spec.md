# agent-usage-records Specification

## Purpose

Provide durable, provider-faithful accounting for managed agents using structured headless output and bound native session logs, with explicit scope, availability, provenance, and resumable incremental retrieval.

## Requirements

### Requirement: Usage records carry stable accounting identities

Each record SHALL identify its schema version, logical agent, runtime session, accounting turn, backend, provider, and known provider session, provider turn, and registry generation. Records SHALL distinguish managed turns from native-observed turns. A provider turn index alone SHALL NOT establish accounting identity.

#### Scenario: Failed-turn retry retains distinct identity

- **WHEN** two managed attempts receive the same provider turn index after an earlier attempt fails
- **THEN** they retain distinct accounting turn IDs and usage-record IDs

#### Scenario: Native turn rediscovery preserves identity

- **WHEN** a collector rediscovers a finalized native turn in the same runtime session
- **THEN** the record retains its native-observed origin and stable accounting identity
- **AND THEN** a correlated managed submission and its native turn produce one accounting record

### Requirement: Collection is bound to the managed provider session

Collection SHALL use a verified binding between the managed agent, provider home, and provider session. It SHALL establish a launch or attachment boundary and SHALL NOT charge earlier history as new work. Shared directories or modification times alone SHALL NOT establish ownership.

#### Scenario: Attachment excludes prior history

- **WHEN** collection attaches to a provider session containing earlier completed turns
- **THEN** earlier usage is excluded from new accounting
- **AND THEN** any earlier evidence read to establish a baseline remains nonchargeable

#### Scenario: Shared home does not merge unrelated sessions

- **WHEN** a provider home contains logs for the bound agent and another session
- **THEN** only evidence whose ownership is established by the binding contributes to that agent's accounting

#### Scenario: Attachment occurs during an existing turn

- **WHEN** collection starts after a native turn has begun
- **THEN** any accounting for that turn declares its incomplete coverage
- **AND THEN** the record does not claim a complete measurement of pre-attachment work

### Requirement: Accounting capability follows validated evidence

Capability SHALL identify validated source kinds, observed measurement scopes, turn-recording support, and unavailable or degraded reasons. Execution mode alone SHALL NOT determine support. Session-only evidence SHALL NOT imply supported per-turn measurements.

#### Scenario: Qualified TUI source exposes usage

- **WHEN** a TUI agent has a validated native source with verified turn association and final outcome
- **THEN** its finalized usage is available through the shared accounting contract

#### Scenario: Session-only evidence remains limited

- **WHEN** a native source exposes session totals without reliable turn boundaries
- **THEN** capability identifies session-level evidence and unavailable per-turn accounting
- **AND THEN** no fabricated per-turn token record is emitted

#### Scenario: Missing source preserves known history

- **WHEN** a previously supported source becomes unreadable or unsupported
- **THEN** capability reports the collection limitation
- **AND THEN** already finalized history remains readable

### Requirement: Accounting metrics expose availability and provenance

Each measurement SHALL expose availability, units, scope, source references, and reported or derived provenance. Missing values SHALL remain null or explicitly unavailable. A reported zero SHALL remain distinguishable from an absent field, and derived values SHALL identify the rule and evidence used.

#### Scenario: Missing cached tokens remain unknown

- **WHEN** a provider reports input and output tokens but omits cost and cached-token counts
- **THEN** available counters are preserved while the omitted measurements remain unavailable

#### Scenario: Explicit zero remains reported zero

- **WHEN** a provider reports zero cached tokens and omits cost
- **THEN** cached tokens retain value zero with reported provenance and cost remains unavailable

### Requirement: Usage extraction preserves structured provider evidence

Accounting SHALL use validated structured provider payloads and lifecycle metadata independently of display formatting. It SHALL preserve distinct reported cache, reasoning, cost, and timing fields. Context occupancy, terminal text, and generated character counts SHALL NOT substitute for accounting.

#### Scenario: Full Codex usage fields remain distinct

- **WHEN** structured Codex evidence reports input, cached input, cache-write input, output, and reasoning output
- **THEN** each reported field remains separately available in accounting

#### Scenario: Kimi without usable usage evidence stays unavailable

- **WHEN** a Kimi turn has output and completion evidence but no validated structured usage source
- **THEN** its token metrics remain unavailable without a text-derived estimate

### Requirement: Request and cumulative scopes are distinguished

Extraction SHALL distinguish request measurements, turn summaries, and session-cumulative snapshots using validated provider semantics. Event names alone SHALL NOT establish scope. Additive per-turn metrics SHALL contain only measurements attributed to that turn.

#### Scenario: Codex completion carries cumulative totals

- **WHEN** a Codex completion event contains cumulative thread usage
- **THEN** that payload is treated as cumulative evidence rather than an additive turn measurement

#### Scenario: Provider emits request and session records

- **WHEN** a provider emits request increments and session totals covering the same work
- **THEN** accounting uses a validated representation for the turn without adding both representations

### Requirement: Cumulative derivation requires a verified baseline

A cumulative delta SHALL require comparable measurements from the same bound provider session and counter epoch. Missing baselines, counter discontinuities, and uncertain coverage SHALL produce partial or unavailable turn metrics rather than fabricated zero or full-session charges.

#### Scenario: Two resumed turns are counted once

- **WHEN** a verified new session starts at zero and finalized totals progress from 1000 to 1600 across two turns
- **THEN** derived turn increments are 1000 and 600 with derivation provenance

#### Scenario: Resume has no verified baseline

- **WHEN** collection receives a cumulative completion total for resumed history without a comparable starting baseline
- **THEN** it does not charge the full total to the new turn

#### Scenario: Counter decreases unexpectedly

- **WHEN** a cumulative counter decreases without a validated reset explanation
- **THEN** accounting reports the discontinuity and leaves affected turn metrics partial or unavailable

### Requirement: Token overlap semantics prevent double counting

Normalized accounting SHALL document whether cache counts are included in input and whether reasoning is included in output. Totals SHALL come from reported values or validated derivations with explicit provenance. Unsupported formulas SHALL leave totals unavailable.

#### Scenario: Cached input and reasoning are subsets

- **WHEN** provider evidence establishes that cached input is included in input and reasoning is included in output
- **THEN** neither subset is added again to the total

#### Scenario: Missing total has no verified formula

- **WHEN** component counters exist but neither a total nor a validated total formula is available
- **THEN** total tokens remain unavailable

### Requirement: Duplicate and overlapping evidence is counted once

The same provider request SHALL contribute at most once when repeated across structured output, native logs, resumed transcripts, or copied fork/subagent history. A verified summary and its constituent requests SHALL NOT both contribute to the same measurement. Unresolved conflicting evidence SHALL remain explicit.

#### Scenario: Stdout and transcript repeat one request

- **WHEN** the same provider response is observed in stdout and a native transcript
- **THEN** its counters contribute once and provenance retains the relevant evidence references

#### Scenario: Fork replays parent usage

- **WHEN** a child transcript repeats parent request history before its own work
- **THEN** inherited history is excluded while distinct child requests remain eligible for accounting

#### Scenario: Summary replaces constituent measurements

- **WHEN** a verified turn summary covers request measurements already collected for that turn
- **THEN** the summary supplies the applicable turn measurement without adding its constituent values again

### Requirement: Native turn association requires structured evidence

Native-observed records SHALL require verified provider turn identity and terminal outcome. Existing hooks SHALL serve only as validated identity or lifecycle evidence, not as token measurements. Ambiguous time windows or terminal appearance alone SHALL NOT assign usage to a turn.

#### Scenario: Direct human TUI turn is observed

- **WHEN** a human enters a prompt directly in a bound TUI and structured evidence identifies its turn and final outcome
- **THEN** a native-observed record uses the shared schema and stream

#### Scenario: Turn identity is ambiguous

- **WHEN** usage is available but its association with a finalized turn cannot be verified
- **THEN** the evidence is retained with its actual scope and no falsely attributed per-turn measurement is emitted

#### Scenario: Native completion precedes managed association

- **WHEN** a native turn finishes while association with a pending managed submission is unresolved
- **THEN** accounting waits for verified association or reports the limitation
- **AND THEN** managed and native finalization do not emit separate charges for the same turn

### Requirement: Every instrumented managed headless outcome produces a final record

Every instrumented managed headless turn that completes, fails, or is interrupted SHALL produce one final record using durable evidence. A terminal outcome with no usage SHALL retain unavailable metrics. Active turns SHALL remain outside the finalized stream.

#### Scenario: Failed or interrupted turn preserves partial usage

- **WHEN** a headless turn reaches failed or interrupted outcome with partial usage evidence
- **THEN** its final record preserves that evidence, outcome, and available timing

#### Scenario: Controller timeout leaves execution active

- **WHEN** a controller times out while the provider process remains active
- **THEN** the turn remains pending for accounting until terminal evidence establishes its outcome

### Requirement: Finalization is immutable and idempotent

Equivalent finalization or reconciliation of one accounting turn SHALL produce at most one immutable record. Finalization SHALL use a durable evidence cutoff and terminal facts. Conflicting repeats SHALL report an error without changing consumed history.

#### Scenario: Repeated completion is a no-op

- **WHEN** two paths finalize the same turn with equivalent durable evidence
- **THEN** one record and one stream position exist

#### Scenario: Later evidence conflicts with final accounting

- **WHEN** new evidence would change an already finalized record
- **THEN** the original remains unchanged and the conflict is reported explicitly

### Requirement: Native collection resumes without loss or replay charges

Collection progress and accepted observations SHALL survive process restarts without skipping evidence or charging it twice. Partial trailing records, file replacement, and truncation SHALL receive explicit handling.

#### Scenario: Crash occurs during ingestion

- **WHEN** a collector stops while accepting a batch and advancing its source position
- **THEN** recovery either reprocesses the batch idempotently or resumes after its durably accepted observations

#### Scenario: Last JSONL line is incomplete

- **WHEN** a native log ends with an incomplete record
- **THEN** the collector waits for completion without losing that record on the next read

#### Scenario: Source file is replaced or truncated

- **WHEN** the bound source changes file identity or loses previously read content
- **THEN** collection validates continuity before deriving further deltas
- **AND THEN** prior requests are not charged again merely because file positions changed

### Requirement: Usage history survives controlling-process restarts

Final history and its stream positions SHALL persist independently of gateway or passive-server lifetime. Incompatible or unreadable storage SHALL fail explicitly without modifying gateway queue storage.

#### Scenario: Restart preserves history

- **WHEN** a controller restarts after records were finalized
- **THEN** records, IDs, and stream positions remain readable without reconstructing existing history from provider logs

### Requirement: Incremental retrieval uses bounded finalization-order pages

Records SHALL be returned in per-runtime-session finalization order using opaque stream-bound cursors and bounded pages. A queryable stream SHALL return a resumable cursor even when no further records currently exist. Late finalization SHALL receive a later stream position.

#### Scenario: Polling resumes after the last page

- **WHEN** a caller saves the cursor from a page with no further records and another turn later finalizes
- **THEN** polling after that cursor returns the new record without repeating earlier records

#### Scenario: Empty stream later receives its first record

- **WHEN** a caller saves the cursor from an initially empty queryable stream
- **THEN** the same cursor can retrieve the first later-finalized record

#### Scenario: Late failure remains visible

- **WHEN** an older turn finalizes after a newer turn has entered the stream
- **THEN** the older turn appears at a later stream position

### Requirement: Reset and relaunch semantics preserve attribution

Provider-chat reset SHALL preserve the runtime-session stream while establishing a distinct source binding or counter epoch. Relaunch SHALL preserve existing history and attribute later turns to the applicable generation. A new runtime session SHALL have a distinct stream.

#### Scenario: Relaunch does not relabel older usage

- **WHEN** recovery finalizes an older turn after the agent has relaunched
- **THEN** that record uses its original turn-start generation and later records use the new generation

#### Scenario: Provider reset does not reuse the old baseline

- **WHEN** a provider chat resets within the runtime session
- **THEN** its new measurements do not subtract a baseline from the previous chat

### Requirement: Private-subagent accounting is explicit

Records SHALL declare private-subagent accounting as included, separate, excluded, or unknown. Separately reported measurements SHALL identify their parent turn and whether they overlap the parent's totals. Task events alone SHALL NOT establish inclusion.

#### Scenario: Inclusion is unknown

- **WHEN** available provider evidence does not establish subagent inclusion
- **THEN** accounting reports unknown rather than assuming inclusion or exclusion

#### Scenario: Separate child measurements overlap a summary

- **WHEN** a provider identifies child measurements and establishes that a parent summary already includes them
- **THEN** the child breakdown remains linked without being added to the parent total again

### Requirement: Missed final records are reconciled without duplication

Recovery SHALL reconcile durably finalized turns whose records were not persisted, using their original identities, outcomes, timing, and evidence cutoff. A recovered record SHALL enter the stream once in reconciliation order.

#### Scenario: Recorder outage is recovered

- **WHEN** terminal evidence exists but the recorder stopped before persisting the final record
- **THEN** recovery inserts the missing record once with its original accounting identity and a new finalization sequence

### Requirement: Public evidence contains accounting data only

Public records SHALL expose only allowlisted accounting evidence and safe provenance. Prompts, responses, tool content, credentials, environment values, and private source paths SHALL NOT appear in usage responses.

#### Scenario: Structured provider event contains private content

- **WHEN** an input event contains accounting fields alongside prompt, tool, or credential data
- **THEN** the usage response includes only the allowed accounting fields and safe source references
