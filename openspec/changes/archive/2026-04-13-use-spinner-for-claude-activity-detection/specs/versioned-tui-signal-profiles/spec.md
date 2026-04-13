## MODIFIED Requirements

### Requirement: Profiles may delegate drift-prone surface regions to behavior variants
The shared versioned TUI profile contract SHALL allow a selected app profile to delegate interpretation of one drift-prone prompt, status, or activity-evidence region to a profile-owned behavior variant.

That behavior variant SHALL consume raw snapshot-derived region content and MAY rely on rendering or style evidence, including raw ANSI/SGR state, cursor or prompt-marker styling, or latest-turn region scoping, when stripped text alone is insufficient to classify the region safely.

The behavior variant SHALL return a coarse profile-local classification that the selected profile can translate into normalized tracker signals.

The shared tracker engine SHALL remain unaware of behavior-variant internals and SHALL continue to depend only on the selected profile's normalized outputs.

For prompt-area, status-region, or activity-evidence interpretation, behavior variants SHALL remain profile-private implementation details of the selected app detector profile rather than separate shared registry entries.
For transcript-style UIs that retain older terminal text on screen, a selected profile MAY use the last visible current-prompt anchor as a stateless latest-turn boundary and MAY degrade conservatively when no such anchor is visible rather than falling back to full-transcript terminal matching.
For transcript-style UIs that retain older activity rows on screen, a selected profile SHALL NOT expose historical spinner, structured progress, or active block rows above the current latest-turn boundary as current active-turn evidence by themselves.
For Claude Code activity-evidence interpretation, a selected profile SHALL NOT treat fixed thinking or tool-activity prose phrases as current active-turn evidence by themselves. It MAY treat structural current-turn indicators such as spinner-glyph rows, interruptable footer posture, and current active block shape as active-turn evidence.
For prompt-payload interpretation, a selected profile MAY treat foreground/background color-setting families and their resets as neutral rendering noise while still treating dim, inverse, or other non-color styles as meaningful evidence.

#### Scenario: Codex prompt interpretation is delegated through the selected profile
- **WHEN** the tracker resolves a Codex TUI profile for an observed Codex version
- **AND WHEN** that profile needs to interpret the prompt area for editing semantics
- **THEN** the selected profile may invoke its profile-owned prompt behavior variant for that version family
- **AND THEN** the shared tracker engine still consumes only normalized Codex signals

#### Scenario: Claude prompt interpretation can use style-aware draft classification
- **WHEN** the tracker resolves a Claude Code profile for an observed Claude version family
- **AND WHEN** that profile needs to distinguish styled placeholder text, prompt-marker styling, and real typed draft input on the visible prompt line
- **THEN** the selected profile may invoke a profile-owned prompt behavior variant that uses raw prompt rendering and style evidence for that version family
- **AND THEN** the shared tracker engine still consumes only normalized Claude signals

#### Scenario: Claude status interpretation can ignore stale transcript terminal text
- **WHEN** the tracker resolves a Claude Code profile for an observed Claude version family
- **AND WHEN** older interrupted or failure status lines remain visible in transcript history above the current turn region
- **THEN** the selected profile may invoke a profile-owned status-region behavior variant that scopes terminal evidence to the latest turn region using the last visible prompt anchor as a stateless boundary
- **AND THEN** the shared tracker engine does not require global screen-wide status matching to decide the current turn state

#### Scenario: Claude status interpretation degrades conservatively when no current prompt anchor is visible
- **WHEN** the tracker resolves a Claude Code profile for an observed Claude version family
- **AND WHEN** no current prompt anchor is visible for the latest turn region
- **THEN** the selected profile may degrade conservatively instead of asserting interrupted or known-failure state from older transcript text alone
- **AND THEN** the shared tracker engine does not need inter-snapshot detector state to avoid stale terminal matches

#### Scenario: Claude activity interpretation ignores historical activity rows
- **WHEN** the tracker resolves a Claude Code profile for an observed Claude version family
- **AND WHEN** older spinner, structured progress, or active block rows remain visible in transcript history above the current turn region
- **AND WHEN** the current turn region contains a submit-ready prompt and no current structural active evidence
- **THEN** the selected profile does not expose those historical rows as current active-turn evidence
- **AND THEN** the shared tracker engine can report the current prompt-ready state without a stale active reason from transcript history

#### Scenario: Claude activity interpretation ignores prose-only thinking and tool text
- **WHEN** the tracker resolves a Claude Code profile for an observed Claude version family
- **AND WHEN** the current captured surface contains fixed thinking or tool-activity prose text without a current spinner, interruptable footer, or current active block structure
- **AND WHEN** the current prompt is otherwise submit-ready
- **THEN** the selected profile does not expose that prose text as current active-turn evidence
- **AND THEN** the shared tracker engine can keep the current prompt-ready posture instead of downgrading it to active

#### Scenario: Claude activity interpretation preserves current spinner rows
- **WHEN** the tracker resolves a Claude Code profile for an observed Claude version family
- **AND WHEN** a spinner-glyph activity row is visible as current-turn structural evidence
- **THEN** the selected profile may expose current active-turn evidence from that spinner row
- **AND THEN** the shared tracker engine may report the current turn as active from normalized Claude signals

#### Scenario: Claude activity interpretation preserves current interruptable active blocks
- **WHEN** the tracker resolves a Claude Code profile for an observed Claude version family
- **AND WHEN** a current active response block or tool block is paired with current interruptable footer posture
- **THEN** the selected profile may expose current active-turn evidence from that structural activity surface
- **AND THEN** the shared tracker engine may report the current turn as active from normalized Claude signals

#### Scenario: Claude prompt interpretation can ignore color-only marker styling
- **WHEN** the tracker resolves a Claude Code profile for an observed Claude version family
- **AND WHEN** the visible prompt marker or prompt payload includes only foreground/background color-setting SGR families and their resets in addition to real typed draft text
- **THEN** the selected profile may treat those color-setting families as neutral for prompt-payload classification
- **AND THEN** dim, inverse, or other non-color styles may still influence placeholder-versus-draft classification for that version family

#### Scenario: Drifted prompt or status behavior is updated without rewriting the shared engine
- **WHEN** a future supported TUI version changes how placeholder text, current draft text, current terminal status, or current activity evidence appears in one prompt, status, or activity-evidence region
- **THEN** maintainers can update the affected behavior variant or add a new version-family profile that selects a different variant
- **AND THEN** unrelated shared tracker engine logic and other app profiles do not require a coordinated rewrite

#### Scenario: Behavior variants remain profile-private in v1
- **WHEN** the repository introduces or updates version-selected prompt, status, or activity-evidence behavior variants for Codex, Claude, or another supported interactive TUI profile
- **THEN** those variants remain owned by the selected app detector profile
- **AND THEN** the shared registry does not grow separate top-level entries for those behavior variants in this change
