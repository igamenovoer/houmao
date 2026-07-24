## MODIFIED Requirements

### Requirement: Recorded validation SHALL compare replayed public tracked state against ground truth

The restored recorded-validation workflow SHALL compare human-authored ground truth against the tracker’s public tracked state rather than against raw pane text or internal detector intermediates.

The strict comparison target SHALL remain the public tracked-state fields used by downstream dashboards and reports:

- `diagnostics_availability`
- `surface_accepting_input`
- `surface_editing_input`
- `surface_ready_posture`
- `surface_pending_input`
- `turn_phase`
- `last_turn_result`
- `last_turn_source`

The harness SHALL expand `labels.json` into a complete per-sample public-state timeline and SHALL compare replay output against that public-state timeline sample by sample.

#### Scenario: Strict replay validation judges public tracked state per sample

- **WHEN** a maintainer runs `recorded-validate` on one restored fixture root
- **THEN** the workflow expands ground truth from `labels.json` into a complete per-sample public-state timeline
- **AND THEN** it replays the recorded evidence into the shared tracker and compares the replayed public state against ground truth sample by sample

## ADDED Requirements

### Requirement: Recorded pending-input qualification uses audited labels and cadence variants

Before pending-input recordings are used as acceptance evidence, a maintainer SHALL review their rendered pane/label videos, correct label boundaries as needed, and record the observed provider version provenance. Analyzer-generated pattern labels SHALL remain calibration input rather than the sole correctness oracle.

Pending-input qualification SHALL run the canonical high-rate recording plus derived low-rate and seeded irregular-cadence variants. Reports SHALL separate detector mismatches, skipped unobserved transitions, provider queue caps, and tainted capture evidence.

#### Scenario: Pattern-generated labels require human audit

- **WHEN** a UC05 pending-input dataset was labeled from the same provider patterns that drove capture
- **THEN** the dataset is not treated as final qualification ground truth until a maintainer audits its review video and records any corrections
- **AND THEN** the qualification report distinguishes generated labels from audited labels

#### Scenario: Claude version discrepancy blocks unqualified acceptance

- **WHEN** Claude recording metadata names a different version from the version visible in the recorded pane
- **THEN** the discrepancy is corrected or explicitly resolved before the run is counted as qualified evidence
- **AND THEN** the selected detector profile and report identify the resolved version provenance

#### Scenario: Multi-count captures validate binary presence

- **WHEN** audited recordings contain one, two, or three provider-native pending instructions
- **THEN** strict validation expects `surface_pending_input=yes` across each decisive pending span
- **AND THEN** any provider cap or tainted count run is reported instead of being counted as full multi-count coverage
