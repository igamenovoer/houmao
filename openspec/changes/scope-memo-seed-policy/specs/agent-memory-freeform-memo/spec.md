## ADDED Requirements

### Requirement: Memo-only launch-profile seeds preserve pages
When applying a launch-profile memo seed that represents only `houmao-memo.md`, Houmao SHALL treat the seed as an explicit memo operation and SHALL NOT inspect, clear, or rewrite the contained `pages/` tree.

Memo-only seeds include inline text seeds, file seeds, and directory seeds that contain `houmao-memo.md` without `pages/`.

#### Scenario: Memo-only replace leaves pages unchanged
- **WHEN** a launch profile stores inline memo seed text with policy `replace`
- **AND WHEN** the target managed memory already contains `pages/notes/start.md`
- **THEN** Houmao replaces `houmao-memo.md` from the seed
- **AND THEN** it leaves `pages/notes/start.md` unchanged

#### Scenario: Empty memo-only replace leaves pages unchanged
- **WHEN** a launch profile stores inline memo seed text `""` with policy `replace`
- **AND WHEN** the target managed memory already contains `pages/notes/start.md`
- **THEN** Houmao writes an empty `houmao-memo.md`
- **AND THEN** it leaves `pages/notes/start.md` unchanged
