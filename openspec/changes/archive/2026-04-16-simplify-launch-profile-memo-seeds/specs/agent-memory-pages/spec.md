## MODIFIED Requirements

### Requirement: Page-scoped launch-profile seeds preserve memo
When applying a launch-profile directory memo seed that represents pages but does not represent `houmao-memo.md`, Houmao SHALL treat the seed as an explicit pages operation and SHALL NOT inspect, replace, or clear the memo file.

A represented pages target SHALL clear then rewrite only the contained `pages/` tree. An empty `pages/` directory in the seed SHALL represent an intentional request to clear pages.

#### Scenario: Pages-only seed leaves memo unchanged
- **WHEN** a launch profile stores a directory memo seed containing `pages/notes/start.md` and no `houmao-memo.md`
- **AND WHEN** the target managed memory already contains `houmao-memo.md`
- **THEN** Houmao replaces contained pages from the seed
- **AND THEN** it leaves `houmao-memo.md` unchanged

#### Scenario: Empty pages seed clears pages only
- **WHEN** a launch profile stores a directory memo seed containing an empty `pages/` directory and no `houmao-memo.md`
- **AND WHEN** the target managed memory already contains `houmao-memo.md` and one page under `pages/`
- **THEN** Houmao clears the contained pages
- **AND THEN** it leaves `houmao-memo.md` unchanged
