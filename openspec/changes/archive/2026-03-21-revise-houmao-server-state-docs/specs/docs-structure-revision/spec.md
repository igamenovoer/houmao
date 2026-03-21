## ADDED Requirements

### Requirement: Audience-based reading paths in index
The restructured `docs/developer/houmao-server/index.md` SHALL present four distinct reading paths: (1) **State Reference** for "what does this value mean?" lookups, (2) **Transitions & Operations** for "what can I do in this state?" guidance, (3) **Pipeline Architecture** for "how does the tracker build state?" deep-dives (existing `state-tracking.md`), and (4) **Internals** for registration, probe/parse pipeline, supervisor lifecycle, and live state model details (relocated from migration docs).

#### Scenario: Four reading paths visible
- **WHEN** a reader opens the developer guide index
- **THEN** the page presents four clearly labeled reading paths with one-line descriptions and links to the corresponding docs

#### Scenario: State reference path links to new guide
- **WHEN** a reader follows the State Reference path
- **THEN** they arrive at the new state reference guide document

#### Scenario: Transitions path links to new guide
- **WHEN** a reader follows the Transitions & Operations path
- **THEN** they arrive at the new state transitions and operations guide document

#### Scenario: Architecture path links to existing doc
- **WHEN** a reader follows the Pipeline Architecture path
- **THEN** they arrive at the existing `state-tracking.md`

#### Scenario: Internals path links to relocated docs
- **WHEN** a reader follows the Internals path
- **THEN** they arrive at `internals/README.md` which provides the reading order for registration, pipeline, live state model, and supervisor docs

### Requirement: Relocate internals from migration to developer
The five TUI handling internals docs (`README.md`, `registration_and_discovery.md`, `probe_parse_track_pipeline.md`, `supervisor_and_lifecycle.md`, `live_state_model.md`) SHALL be moved from `docs/migration/houmao/internals/tui_handling/` to `docs/developer/houmao-server/internals/`. All relative source-file paths within the relocated files SHALL be updated to reflect the new directory depth. A redirect note SHALL be left at the old location pointing to the new developer home. The `docs/migration/houmao/server-pair/README.md` reading order SHALL be updated to point to the new developer location.

#### Scenario: Internals docs exist under developer directory
- **WHEN** a developer looks for houmao-server internals documentation
- **THEN** the docs are found at `docs/developer/houmao-server/internals/`

#### Scenario: Old migration location has redirect
- **WHEN** a reader visits `docs/migration/houmao/internals/tui_handling/`
- **THEN** they find a redirect note pointing to `docs/developer/houmao-server/internals/`

#### Scenario: Migration server-pair README updated
- **WHEN** a reader opens `docs/migration/houmao/server-pair/README.md`
- **THEN** the reading order links point to `docs/developer/houmao-server/internals/` instead of the old migration location

#### Scenario: Relative source paths updated in relocated files
- **WHEN** a reader opens any relocated internals file
- **THEN** all relative links to `src/houmao/server/` resolve correctly from the new directory depth

### Requirement: Deduplicate live_state_model.md via cross-references
After relocation, `docs/developer/houmao-server/internals/live_state_model.md` SHALL replace its duplicated diagnostics mapping, surface observables, and turn/last-turn mapping sections with brief summaries plus links to the new `state-reference.md`. Content specific to the internals perspective (identity/aliases, initial state, internal timing and authority notes) SHALL remain in place.

#### Scenario: Diagnostics mapping replaced with cross-reference
- **WHEN** a reader opens the relocated `live_state_model.md`
- **THEN** the diagnostics mapping section contains a brief summary and a link to `state-reference.md` for full definitions

#### Scenario: Internals-specific content preserved
- **WHEN** a reader opens the relocated `live_state_model.md`
- **THEN** the Identity And Aliases section, Initial State section, and Internal Timing And Authority section remain intact with their original content

### Requirement: Migration docs remain focused on CAO-to-houmao transition
After relocation, `docs/migration/houmao/` SHALL contain only migration-focused content: `server-pair/README.md` (what was implemented and how to adopt), `server-pair/migration-guide.md` (step-by-step transition from CAO to houmao), and `server-pair/tested.md` (verification scope). No houmao-server internal architecture documentation SHALL remain under `docs/migration/`.

#### Scenario: No internals docs remain under migration
- **WHEN** a reviewer lists files under `docs/migration/houmao/internals/tui_handling/`
- **THEN** only a redirect note exists, not the original internals documents

### Requirement: Consistent source-of-truth pointers across all docs
Every documentation file that references state values SHALL include a pointer to the state reference guide as the maintained definition location, and to `src/houmao/shared_tui_tracking/models.py` as the canonical code source for type definitions and `src/houmao/shared_tui_tracking/public_state.py` for mapping logic. References to `src/houmao/server/models.py` SHALL describe it as the re-export surface for server Pydantic response models.

#### Scenario: State-tracking.md references the state reference guide
- **WHEN** a reader opens `state-tracking.md`
- **THEN** the Public Contract section includes a note pointing to the state reference guide for full value definitions and operational implications

### Requirement: Source Of Truth Map updated for shared module
The restructured `docs/developer/houmao-server/index.md` Source Of Truth Map SHALL include `src/houmao/shared_tui_tracking/models.py`, `src/houmao/shared_tui_tracking/public_state.py`, `src/houmao/shared_tui_tracking/detectors.py`, and `src/houmao/shared_tui_tracking/reducer.py` alongside the existing server source files. The map SHALL note that core state type definitions and mapping logic live in `shared_tui_tracking/`, not `server/models.py`.

#### Scenario: Shared module files listed in source map
- **WHEN** a reader opens the developer guide index
- **THEN** the Source Of Truth Map includes `shared_tui_tracking/models.py`, `shared_tui_tracking/public_state.py`, `shared_tui_tracking/detectors.py`, and `shared_tui_tracking/reducer.py`

### Requirement: Route references use Houmao-native paths
All route references in new and updated documentation files SHALL use Houmao-native paths (`/houmao/terminals/{terminal_id}/state`, `/houmao/terminals/{terminal_id}/input`, `/houmao/terminals/{terminal_id}/history`) and SHALL NOT reference legacy root-level CAO-compatible paths.

#### Scenario: No legacy root routes in docs
- **WHEN** a reviewer searches new and updated docs for route patterns
- **THEN** no occurrences of `/terminals/{id}/state` or `/terminals/{id}/input` without the `/houmao/` prefix are found
