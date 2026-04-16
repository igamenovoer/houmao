## MODIFIED Requirements

### Requirement: CLI reference explains component-scoped memo seed policies
The `houmao-mgr` CLI reference SHALL explain that launch-profile memo seeds do not expose a memo seed policy option.

The CLI reference SHALL explain that memo seed source options replace only the managed-memory components represented by the supplied source.

When the reference documents `--memo-seed-text` or `--memo-seed-file`, it SHALL state that profile-backed launch replaces `houmao-memo.md` without clearing memory pages.

When the reference documents `--memo-seed-dir`, it SHALL state that a directory seed replaces `houmao-memo.md` only when `houmao-memo.md` is present and replaces pages only when `pages/` is present.

When the reference documents `--clear-memo-seed`, it SHALL distinguish removing stored seed configuration from storing an empty memo seed.

#### Scenario: Reader distinguishes empty memo seed from clearing seed config
- **WHEN** a reader looks up memo seed flags for launch profiles or easy profiles
- **THEN** the CLI reference states that `--clear-memo-seed` removes stored seed configuration
- **AND THEN** the CLI reference states that `--memo-seed-text ''` stores an intentional empty memo seed
- **AND THEN** the CLI reference does not document `--memo-seed-policy`

#### Scenario: Reader sees memo-only seed preserves pages
- **WHEN** a reader looks up `--memo-seed-text`
- **THEN** the CLI reference states that the launch replaces `houmao-memo.md`
- **AND THEN** it does not state that pages are cleared for memo-only seeds
