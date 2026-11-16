# Spec Delta

## ADDED Requirements

### Requirement: DSH Consumption Uses Qualified Native Journal Evidence

DSH accounting SHALL use a qualified native journal bound to the managed home and exact native session. ACP context-occupancy updates SHALL remain distinct from consumed-token measurements. Unsupported journal formats, missing evidence, or unreadable sources SHALL produce explicit collection limitations while preserving finalized history.

#### Scenario: ACP Reports Occupancy Without Consumption
- **WHEN** ACP exposes a usage update with used context and capacity but the journal has no valid provider token sample
- **THEN** consumption metrics remain unavailable
- **AND THEN** the occupancy value is not charged as input or total tokens

#### Scenario: Native Journal Encoding Is Unsupported
- **WHEN** a bound DSH journal has an unqualified format or encoding
- **THEN** collection reports the unsupported source without interpreting arbitrary lines or erasing earlier records

### Requirement: DSH Request Attempts Contribute Once

DSH accounting SHALL distinguish native turns, steps, provider attempts, and inherited history. Repeated samples within one attempt SHALL not become repeated charges; separately billed retries SHALL remain distinct. Failed or interrupted attempts SHALL preserve reported usage, and absent measurements SHALL remain unknown.

#### Scenario: A Step Retries a Billed Request
- **WHEN** a native step records usage for a failed attempt and usage for a later retry
- **THEN** both distinct settled attempts contribute once when their lifecycle evidence establishes separate requests

#### Scenario: A Settled Message Repeats an Attempt Sample
- **WHEN** the same provider attempt's usage appears in its embedded stream and settled message metadata
- **THEN** the selected authoritative sample contributes once with provenance for the source evidence

#### Scenario: Interrupted Work Has No Reported Usage
- **WHEN** a DSH attempt terminates before any valid provider usage is preserved
- **THEN** its final record retains the outcome with unavailable token metrics instead of zero-valued estimates

### Requirement: DSH Token Normalization Preserves Disjoint Buckets

DSH uncached input, cache-read input, cache-write input, output, reasoning, and exact reported totals SHALL retain their validated meanings. Normalized totals SHALL use reported values or a verified formula with explicit provenance. Missing cache buckets SHALL not be assumed zero, and reasoning already included in output SHALL not be added again.

#### Scenario: DSH Reports All Disjoint Input Buckets
- **WHEN** a request reports uncached input, cache reads, cache writes, and output under the qualified DSH contract
- **THEN** normalization records each bucket and derives aggregate input or total only through the validated disjoint-bucket formula

#### Scenario: A Cache Bucket Is Absent
- **WHEN** a request omits a cache bucket and supplies no exact total that resolves the missing measurement
- **THEN** the affected aggregate remains partial or unavailable
- **AND THEN** an explicitly reported zero remains distinguishable from the missing bucket

### Requirement: A DSH Managed Interval Can Cover Multiple Native Turns

One managed DSH submission SHALL be associated with its verified native admission and all proven root activity in its owned interval. Multiple native turns SHALL not force fabricated one-to-one provider identities. Descendant work SHALL identify its actual inclusion scope; unproven association SHALL remain unknown rather than inferred from timing alone.

#### Scenario: A Child Result Starts Another Root Turn
- **WHEN** one ACP prompt remains active across an initial root turn and a later root turn triggered by managed child completion
- **THEN** the managed record includes the proven root attempt evidence once across those native boundaries
- **AND THEN** child measurements identify whether they overlap, are separate, are excluded, or have unknown inclusion

#### Scenario: The Same Interval Is Recovered Twice
- **WHEN** recovery observes the same terminal interval after a controller or recorder restart
- **THEN** the original managed accounting identity and evidence cutoff produce at most one immutable final record

### Requirement: DSH Resume Establishes Nonchargeable Historical Boundaries

Starting or resuming DSH collection SHALL preserve the attachment boundary, journal continuity, accepted offsets, and original terminal facts. Resumed history and copied ancestor evidence SHALL not be charged as new work. A truncated tail or replaced generation SHALL require continuity validation before new measurements are attributed.

#### Scenario: Resume Reads Earlier Completed Turns
- **WHEN** the exact native session contains completed history before the managed turn's starting boundary
- **THEN** those earlier requests remain nonchargeable for the new turn

#### Scenario: Collection Stops Before Its Checkpoint Commits
- **WHEN** collection restarts after reading a DSH request but before advancing its durable checkpoint
- **THEN** ingestion safely reprocesses that evidence without a duplicate usage record
