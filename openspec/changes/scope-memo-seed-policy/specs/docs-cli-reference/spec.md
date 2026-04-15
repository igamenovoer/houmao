## ADDED Requirements

### Requirement: CLI reference explains component-scoped memo seed policies
The `houmao-mgr` CLI reference SHALL explain that `--memo-seed-policy initialize|replace|fail-if-nonempty` applies only to the managed-memory components represented by the supplied memo seed source.

When the reference documents `--memo-seed-text` or `--memo-seed-file`, it SHALL NOT imply that policy `replace` clears memory pages.

When the reference documents `--clear-memo-seed`, it SHALL distinguish removing stored seed configuration from storing an empty memo seed.

#### Scenario: Reader distinguishes empty memo seed from clearing seed config
- **WHEN** a reader looks up memo seed flags for launch profiles or easy profiles
- **THEN** the CLI reference states that `--clear-memo-seed` removes stored seed configuration
- **AND THEN** the CLI reference states that `--memo-seed-text '' --memo-seed-policy replace` stores an intentional empty memo seed

#### Scenario: Reader sees memo-only replace preserves pages
- **WHEN** a reader looks up `--memo-seed-text` with policy `replace`
- **THEN** the CLI reference states that the launch replaces `houmao-memo.md`
- **AND THEN** it does not state that pages are cleared for memo-only seeds
