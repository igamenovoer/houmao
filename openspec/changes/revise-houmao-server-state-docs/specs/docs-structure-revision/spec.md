## ADDED Requirements

### Requirement: Audience-based reading paths in index
The restructured `docs/developer/houmao-server/index.md` SHALL present three distinct reading paths: (1) **State Reference** for "what does this value mean?" lookups, (2) **Transitions & Operations** for "what can I do in this state?" guidance, and (3) **Pipeline Architecture** for "how does the tracker build state?" deep-dives (existing `state-tracking.md`).

#### Scenario: Three reading paths visible
- **WHEN** a reader opens the developer guide index
- **THEN** the page presents three clearly labeled reading paths with one-line descriptions and links to the corresponding docs

#### Scenario: State reference path links to new guide
- **WHEN** a reader follows the State Reference path
- **THEN** they arrive at the new state reference guide document

#### Scenario: Transitions path links to new guide
- **WHEN** a reader follows the Transitions & Operations path
- **THEN** they arrive at the new state transitions and operations guide document

#### Scenario: Architecture path links to existing doc
- **WHEN** a reader follows the Pipeline Architecture path
- **THEN** they arrive at the existing `state-tracking.md`

### Requirement: Migration internals deduplicated via cross-references
The existing `docs/migration/houmao/internals/tui_handling/live_state_model.md` SHALL replace its duplicated diagnostics mapping, surface observables, and turn/last-turn mapping sections with brief summaries plus links to the new state reference guide. Migration-specific content (identity/aliases, initial state, internal timing notes) SHALL remain in place.

#### Scenario: Diagnostics mapping replaced with cross-reference
- **WHEN** a reader opens `live_state_model.md`
- **THEN** the diagnostics mapping section contains a brief summary and a link to the state reference guide for full definitions, instead of duplicating the full mapping table

#### Scenario: Migration-specific content preserved
- **WHEN** a reader opens `live_state_model.md`
- **THEN** the Identity And Aliases section, Initial State section, and Internal Timing And Authority section remain intact with their original content

### Requirement: Consistent source-of-truth pointers across all docs
Every documentation file that references state values SHALL include a pointer to the state reference guide as the maintained definition location, and to `src/houmao/server/models.py` as the canonical code source.

#### Scenario: State-tracking.md references the state reference guide
- **WHEN** a reader opens `state-tracking.md`
- **THEN** the Public Contract section includes a note pointing to the state reference guide for full value definitions and operational implications
