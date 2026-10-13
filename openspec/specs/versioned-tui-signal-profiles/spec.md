## Purpose
Define the shared plugin/profile contract for versioned raw-text TUI signal detection across supported tracker apps.
## Requirements
### Requirement: Supported TUI apps share one plugin and profile contract
The repository SHALL provide one shared plugin/profile contract for official/runtime tracked-TUI detection across supported TUI apps.

That contract SHALL allow each supported app to register:

- an app identifier,
- one or more versioned profiles,
- exact-match or closest-compatible semver-floor profile resolution from observed version metadata, and
- a detection entrypoint that converts one raw TUI snapshot into normalized signals for the shared tracker engine.

The shared tracker boundary SHALL resolve supported apps through this contract rather than through public `tool == ...` branching alone. It SHALL NOT require direct dependency on parser/backend preset registries to resolve tracker profiles.

#### Scenario: Claude Code and Codex use the same tracker extension boundary
- **WHEN** the repository tracks one Claude Code session and one Codex session through the official/runtime tracker
- **THEN** both sessions use the same shared plugin/profile contract to resolve detection behavior
- **AND THEN** the shared tracker engine does not require a separate state-machine implementation per app

### Requirement: Versioned profiles encapsulate app-specific detector suites
Each supported TUI app SHALL be able to define multiple versioned signal profiles under the shared plugin/profile contract.

Each profile SHALL encapsulate the signal-detector set used for that app/version family, and the shared tracker engine SHALL depend only on the profile's normalized detection result rather than on app-specific detector internals.

Profile detection at the shared tracker boundary SHALL derive normalized signals from raw snapshot text, including externally captured direct tmux pane text. Host-provided parsed-surface context SHALL NOT be required by the public tracker contract.

#### Scenario: Closest-compatible profile is selected for an observed version
- **WHEN** the tracker is constructed for a supported app with an observed version that does not require an exact profile match
- **THEN** the plugin resolves the closest-compatible profile for that version
- **AND THEN** the tracker can continue reducing state without requiring a profile per exact patch version

#### Scenario: Host parser metadata is not required for profile detection
- **WHEN** a host already has parser-produced surface metadata for unrelated subsystems
- **THEN** the shared tracker still invokes the selected profile from raw snapshot text alone
- **AND THEN** the host does not need to pass parsed-surface context into the public tracker session

### Requirement: Profile-owned signal evidence remains encapsulated from the shared engine
Signal rules that are specific to one app or version family SHALL remain encapsulated inside that app's selected profile rather than being spread across the shared tracker engine.

The shared engine SHALL consume normalized signals such as active-turn evidence, interruption, known-failure, success-candidate posture, and ready posture, while profile-owned matched-signal details MAY remain available as debugging or testing evidence.
Those profile-owned matched-signal details SHALL NOT be required in the stable public tracker state contract initially.

#### Scenario: Signal drift is corrected by updating a profile rather than the engine
- **WHEN** a supported TUI app changes one visible signal pattern in a new version family
- **THEN** maintainers can update the affected profile-owned detector suite
- **AND THEN** the shared tracker engine does not need an unrelated state-machine rewrite to absorb that drift

### Requirement: Drift-prone failure and retry matching uses bounded semantic patterns
For drift-prone prompt, status, error, warning, or retry surfaces, a selected versioned TUI profile SHALL match current-turn signal families through bounded structural scope plus essential semantic tokens rather than through exact full-sentence literals alone.

Those bounded semantic patterns SHALL remain profile-private implementation details of the selected profile.

The selected profile SHALL scope those patterns to the visual role that the signal plays on the current surface, such as prompt-adjacent terminal failure blocks or live-edge retry status, rather than applying the same matcher to arbitrary historical transcript text.

The shared tracker engine SHALL continue to consume only normalized outputs from the selected profile rather than exact matched text fragments.

#### Scenario: Wording drift within the same failure family still matches
- **WHEN** a supported TUI version changes the wording of a current bounded failure or retry surface while preserving the same essential semantic tokens and visual role
- **THEN** the selected profile can continue to match that current signal family without requiring the previous exact full-sentence literal
- **AND THEN** the shared tracker engine does not require a separate rewrite to absorb that wording drift

#### Scenario: Missing essential semantics do not create a false match
- **WHEN** visible text shares some incidental words with a known failure or retry family but does not carry the essential semantic tokens for that family inside the bounded current-turn region
- **THEN** the selected profile does not classify that surface as that failure or retry family
- **AND THEN** the shared tracker engine does not receive a manufactured stronger lifecycle conclusion from partial word overlap

#### Scenario: Historical text outside the bounded current-turn region does not reuse the same semantic matcher
- **WHEN** a supported TUI transcript still shows older warning, error, or retry text outside the bounded current-turn region
- **THEN** the selected profile does not apply the current-turn semantic matcher to that historical text alone
- **AND THEN** the shared tracker engine can decide the current turn from the bounded present-tense surface instead of from stale transcript wording

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

### Requirement: Claude prompt behavior distinguishes ghost suggestions by style rather than text
For Claude Code profiles that support prompt-payload style analysis, the selected profile SHALL distinguish prompt-line ghost suggestion payloads from user-authored draft input using raw rendering and style evidence from the current prompt region rather than exact suggestion text.

A Claude prompt payload SHALL be eligible for ghost-suggestion classification only when the profile recognizes the payload's non-space characters as rendered wholly in a suggestion style that is visually distinct from ordinary typed prompt text, such as a profile-owned darker or lower-contrast foreground style.

The selected profile SHALL classify such a pure ghost-suggestion payload as placeholder or suggestion content rather than draft input.

The selected profile SHALL classify any prompt payload containing ordinary typed-payload style as draft input, including mixed prompt lines where an operator-typed prefix is followed by a styled suggestion suffix.

The selected profile SHALL remain conservative for unrecognized prompt styling and SHALL NOT classify a non-empty prompt payload as a ghost suggestion solely because the payload text matches a known suggestion phrase.

#### Scenario: Darker arbitrary suggestion text is placeholder content
- **WHEN** the Claude Code prompt line shows a non-empty payload rendered wholly in the profile-recognized darker ghost-suggestion style
- **AND WHEN** the payload text is arbitrary suggestion text rather than a fixed literal
- **THEN** the selected Claude profile classifies the prompt payload as placeholder or suggestion content
- **AND THEN** it does not expose that payload as user-authored draft text

#### Scenario: Changed suggestion wording still classifies from style
- **WHEN** Claude Code changes the visible auto-suggestion wording while preserving the same profile-recognized ghost-suggestion rendering style
- **THEN** the selected Claude profile continues to classify the prompt payload from style evidence
- **AND THEN** it does not require a literal match for the old suggestion text

#### Scenario: Mixed typed prefix and suggestion suffix remains a draft
- **WHEN** the Claude Code prompt line contains an ordinary typed-payload span and a darker styled suggestion span
- **THEN** the selected Claude profile classifies the prompt payload as draft input
- **AND THEN** the shared tracker can preserve the safety rule that user-authored draft input blocks prompt injection

#### Scenario: Unrecognized styled payload degrades conservatively
- **WHEN** the Claude Code prompt line contains non-empty payload text with styling that is neither ordinary typed-payload style nor a profile-recognized ghost-suggestion style
- **THEN** the selected Claude profile does not classify that payload as a ghost suggestion
- **AND THEN** it may report an unknown prompt presentation rather than manufacturing prompt readiness

### Requirement: Tracker app identifiers describe interactive TUI surface families
Tracker app identifiers under the shared profile contract SHALL describe interactive TUI surface families rather than runtime backend names.

For tools that offer both interactive TUI and structured headless control modes, the tracked-TUI profile contract SHALL identify only the interactive surface family that is actually reduced from raw snapshots.

Changing a tracker app identifier SHALL NOT by itself require renaming runtime/backend identifiers that remain outside the tracked-TUI subsystem.

#### Scenario: Codex interactive TUI uses a surface-family app id
- **WHEN** the repository resolves the standalone tracker profile for an interactive Codex TUI session
- **THEN** it resolves that session through a TUI surface-family identifier such as `codex_tui`
- **AND THEN** it does not use a headless backend name as the tracker app identifier

#### Scenario: Headless backend naming does not define tracked-TUI app families
- **WHEN** a runtime backend name exists for a headless or structured Codex control mode
- **THEN** that backend name does not by itself become a tracked-TUI app family in the shared profile registry
- **AND THEN** the tracked-TUI profile contract remains scoped to visible interactive surfaces

#### Scenario: Tracker app-family rename does not imply backend rename
- **WHEN** the tracked-TUI subsystem renames a tracker-facing app identifier from a backend-leaking label to a surface-family label
- **THEN** that rename applies to tracker-facing registry resolution, docs, and tests for the tracked-TUI subsystem
- **AND THEN** runtime/backend identifiers outside the tracked-TUI subsystem remain unchanged unless a separate change targets them

### Requirement: Profiles may contribute temporal hint logic over sliding recent windows
The shared profile contract SHALL allow a profile to contribute temporal hint logic in addition to single-snapshot analysis.

That temporal hint logic SHALL be exposed through a separate temporal-hint callback rather than by changing the meaning of the single-snapshot signal contract.

The temporal callback MAY consume recent ordered profile frames and the injected scheduler to derive profile-owned lifecycle hints from a sliding time window. The contract SHALL NOT require profiles to rely on adjacent-snapshot comparison only.

Profile-specific frame details such as latest-turn-region signatures MAY remain private to the selected profile in v1 rather than widening the shared normalized-signal contract.

#### Scenario: Single-snapshot and temporal profile logic coexist under one profile
- **WHEN** a supported TUI app needs both current-surface matching and recent-window inference
- **THEN** the selected profile may provide both forms of logic under the same shared app/profile contract
- **AND THEN** the shared tracker engine still consumes only normalized profile outputs

#### Scenario: Sliding recent-window inference is preferred over pairwise-only assumptions
- **WHEN** a supported TUI app cannot safely infer state from pairwise-only snapshot comparison because snapshot cadence is externally controlled
- **THEN** its selected profile may use a sliding recent time window for temporal inference
- **AND THEN** the contract does not require profile logic to assume fixed snapshot frequency

#### Scenario: Separate temporal-hint callback preserves the single-snapshot signal contract
- **WHEN** a selected profile derives temporal lifecycle evidence from recent frames
- **THEN** it emits that evidence through a separate temporal-hint callback instead of overloading single-snapshot `DetectedTurnSignals`
- **AND THEN** the shared tracker can trace snapshot facts and temporal hints as distinct inputs before merging them

### Requirement: Kimi signal profiles SHALL be derived from recorded signal contracts
The Kimi Code TUI signal profile SHALL be implemented from the recorded Kimi signal corpus and change-local signal contract artifacts.

The Kimi signal contract SHALL combine live capture evidence with Kimi TUI source-code investigation. Detector rules SHALL identify whether each relied-on signal is source-backed component structure, source-backed styling, temporal behavior observed in capture, or bounded semantics within a known source-backed region.

The profile SHALL prefer minimal stable signals in this order:

1. explicit input events and timing
2. structural anchors in the current surface
3. ANSI/style facts
4. temporal behavior over recent frames
5. bounded semantic tokens inside known visual regions
6. exact string fragments only as diagnostic or fallback evidence

The profile SHALL scope activity and terminal evidence to current-turn or live-edge regions so stale transcript text does not control current state.

#### Scenario: Kimi detector uses structural and style anchors
- **WHEN** the Kimi profile classifies a ready editor or approval dialog
- **THEN** it uses structural anchors and style-aware facts documented in the signal contract
- **AND THEN** it does not depend primarily on one full exact text sentence from Kimi output

#### Scenario: Kimi detector ignores stale transcript activity
- **WHEN** older Kimi activity rows remain visible above the current ready editor region
- **THEN** the Kimi profile does not emit current active-turn evidence from those stale rows alone

#### Scenario: Kimi footer metadata does not imply active state
- **WHEN** a Kimi snapshot contains footer model metadata with `thinking`
- **AND WHEN** the current-turn region has no active response, tool, or spinner evidence
- **THEN** the Kimi profile does not emit active-turn evidence solely from that footer text

### Requirement: Kimi profile implementation SHALL pass recorded validation before maintained support
The Kimi shared TUI tracking profile SHALL pass the labeled Kimi recorded-validation corpus for both high-rate and derived low-rate streams before it is treated as a maintained profile.

The validation gate SHALL include ready, draft, active, completed, approval-blocked, approval-rejected, interrupted, and footer-metadata scenarios across at least 5 development live sessions and at least 3 held-out test live sessions.

Held-out test sessions SHALL NOT be used to choose detector rules, tune temporal thresholds, or revise the Kimi signal contract before the acceptance run.

#### Scenario: Kimi profile passes required scenario families
- **WHEN** Kimi profile implementation is complete
- **THEN** recorded validation passes for the required Kimi scenario families
- **AND THEN** both high-rate and derived low-rate replay outputs match the labeled public tracked-state expectations for development and held-out test sessions

#### Scenario: Held-out sessions guard against overfit detector rules
- **WHEN** Kimi detector rules pass the development corpus but fail held-out Kimi sessions
- **THEN** the Kimi profile is not treated as maintained
- **AND THEN** implementation must revise the signal contract or collect additional evidence before claiming maintained support

#### Scenario: Missing Kimi corpus prevents maintained-profile claim
- **WHEN** no labeled Kimi corpus exists for a required scenario family
- **THEN** the Kimi profile is not treated as maintained for that scenario family
- **AND THEN** implementation must either add the missing capture evidence or narrow its maintained support claim

### Requirement: Kimi Code TUI has a versioned shared signal profile
The shared versioned TUI profile registry SHALL include a Kimi Code TUI app family identified as `kimi_code`.

The Kimi app profile SHALL convert raw Kimi TUI snapshot text into normalized shared tracker signals for prompt readiness, draft editing, active-turn evidence, success-candidate posture, approval-blocked posture, interruption, and known terminal failure families when those families are specifically recognized.

The profile SHALL resolve observed Kimi versions through the same versioned profile selection contract used by other supported TUI apps.

The maintained Kimi Code profile SHALL be qualified against the captured kimi-code `2.1.1` signal corpus. Additional Kimi version families SHALL only be marked maintained when labeled corpus evidence exists for those versions.

#### Scenario: Kimi tool resolves to Kimi tracker app id
- **WHEN** the shared tracker is constructed for tool `kimi`
- **THEN** the tracker resolves the supported TUI app family as `kimi_code`
- **AND THEN** it does not use the `kimi_headless` backend name as the tracker app id

#### Scenario: Kimi idle snapshot emits ready posture
- **WHEN** the Kimi profile receives a raw snapshot with the Kimi editor prompt ready and no current active or blocking surface
- **THEN** it emits normalized ready-posture signals for the shared tracker

#### Scenario: Kimi approval snapshot emits blocked posture
- **WHEN** the Kimi profile receives a raw snapshot with a current command approval dialog
- **THEN** it emits normalized blocking evidence rather than ready-posture evidence

#### Scenario: Kimi active snapshot emits active evidence
- **WHEN** the Kimi profile receives a raw snapshot with current response activity, spinner evidence, or a current tool-use surface
- **THEN** it emits normalized active-turn evidence for the shared tracker

#### Scenario: Kimi footer thinking text is ignored as activity evidence
- **WHEN** the Kimi profile receives a raw snapshot whose only thinking-like text is footer model metadata
- **THEN** it does not emit active-turn evidence solely from that footer text

### Requirement: Kimi Code profile resolution errors below the support floor
Kimi Code tracker profile resolution SHALL support only kimi-code versions at or above the current qualified floor (2.1.1), through exactly one maintained profile with an open-ended semver floor and no kimi fallback profile. An observed version below the floor, or unparseable version metadata, SHALL produce an explicit unsupported-version error at tracker resolution time naming the observed (or missing) version, the required floor, and the migration action (upgrade kimi-code); no detector SHALL be selected for such a session.

#### Scenario: Kimi at the floor resolves the maintained profile
- **WHEN** the tracker resolves app `kimi_code` with observed version `2.1.1`
- **THEN** resolution selects the maintained kimi 2.1.x profile
- **AND THEN** tracked-state reduction proceeds normally

#### Scenario: Kimi below the floor raises an unsupported-version error
- **WHEN** the tracker resolves app `kimi_code` with observed version `0.34.0`
- **THEN** resolution produces an explicit unsupported-version error naming the observed version and the `2.1.1` floor
- **AND THEN** no kimi detector is selected and no tracked state is manufactured for that session

#### Scenario: Unparseable kimi version raises an unsupported-version error
- **WHEN** the tracker resolves app `kimi_code` with missing or unparseable version metadata
- **THEN** resolution produces the same explicit unsupported-version error surface
- **AND THEN** no fallback detector silently scrapes the surface

### Requirement: Kimi profile carries code-side qualified-version metadata
An observed kimi version above the qualified floor SHALL resolve to the maintained kimi profile silently, without any user-facing warning. The kimi registration and profile SHALL carry developer-visible qualified-version metadata (for example, a `qualified_through_version` field or profile note) recording which kimi version the profile was qualified against.

#### Scenario: Kimi above the qualified floor resolves silently
- **WHEN** the tracker resolves app `kimi_code` with observed version `2.3.0`
- **THEN** resolution selects the maintained kimi 2.1.x profile without a user-facing warning
- **AND THEN** developer-visible profile metadata records the version the profile was qualified through

### Requirement: Versioned TUI profile compatibility is bounded
Each maintained detector registration SHALL define the version interval supported by its recorded evidence, either as a bounded interval or as an open-ended floor for a maintained minimum-only registration. The registry SHALL select a profile only when the observed CLI version falls inside that interval.

Versions in gaps or outside every maintained interval SHALL resolve to the conservative app fallback when the app registers one; an app with a floor-gated maintained profile and no fallback (currently `kimi_code`, `codex_tui`, and `claude_code`) SHALL raise an explicit unsupported-version error instead. An explicit experimental override MAY bypass interval matching.

#### Scenario: Newer unvalidated CLI uses fallback
- **WHEN** an observed TUI version is newer than the maximum validated version of every maintained profile for an app that registers a fallback
- **THEN** the registry selects the app's conservative fallback profile
- **AND THEN** it does not silently label the oldest semver-floor profile as compatible

#### Scenario: Below-floor version for a fallback-less app raises
- **WHEN** an observed TUI version falls below the floor of an app that registers no fallback
- **THEN** resolution raises an explicit unsupported-version error naming the observed version and the floor
- **AND THEN** no detector is selected for that session

### Requirement: Current Codex, Kimi, and Claude releases have evidence-backed profiles
The registry SHALL provide a Codex 0.162.x profile qualified against labeled Codex 0.162.1 recordings, a Kimi 2.1.x profile qualified against labeled kimi-code 2.1.1 recordings, and a Claude 2.1.x profile qualified against labeled Claude 2.1.296 recordings. Older Codex 0.116.x and 0.144.x profiles SHALL NOT remain registered because Codex support is floor-gated at 0.162.1 with no fallback; older Kimi profiles SHALL NOT remain registered because Kimi support is floor-gated at 2.1.1 with no fallback; older Claude profiles qualified around 2.1.81 SHALL NOT remain registered because Claude support is floor-gated at 2.1.296 with no fallback.

#### Scenario: Current installed tools resolve current profiles
- **WHEN** tracking observes Codex 0.162.1, Kimi 2.1.1, or Claude 2.1.296
- **THEN** it selects the matching current-version profile
- **AND THEN** detector provenance reports that current profile version

### Requirement: Codex profile resolution errors below the support floor
Codex tracker profile resolution SHALL support only codex at or above the qualified floor (0.162.1), through exactly one maintained profile with an open-ended semver floor and no codex fallback. An observed version below the floor, or unparseable version metadata, SHALL produce an explicit unsupported-version error at tracker resolution naming the observed (or missing) version, the floor, and the migration action (upgrade codex); no detector SHALL be selected for such a session.

#### Scenario: Codex at the floor resolves the maintained profile
- **WHEN** the tracker resolves app `codex_tui` with observed version `0.162.1`
- **THEN** resolution selects the maintained codex 0.162.x profile
- **AND THEN** tracked-state reduction proceeds normally

#### Scenario: Codex below the floor raises an unsupported-version error
- **WHEN** the tracker resolves app `codex_tui` with observed version `0.144.0`
- **THEN** resolution produces an explicit unsupported-version error naming the observed version and the `0.162.1` floor
- **AND THEN** no codex detector is selected and no tracked state is manufactured for that session

#### Scenario: Unparseable codex version raises an unsupported-version error
- **WHEN** the tracker resolves app `codex_tui` with missing or unparseable version metadata
- **THEN** resolution produces the same explicit unsupported-version error surface
- **AND THEN** no fallback detector silently scrapes the surface

### Requirement: Codex profile carries code-side qualified-version metadata
An observed codex version above the qualified floor SHALL resolve to the maintained codex profile silently, without any user-facing warning. The codex registration and profile SHALL carry developer-visible qualified-version metadata (for example, a `qualified_through_version` field or profile note) recording which codex version the profile was qualified against.

#### Scenario: Codex above the qualified floor resolves silently
- **WHEN** the tracker resolves app `codex_tui` with observed version `0.163.0`
- **THEN** resolution selects the maintained codex 0.162.x profile without a user-facing warning
- **AND THEN** developer-visible profile metadata records the version the profile was qualified through

### Requirement: Claude profile resolution errors below the support floor
Claude tracker profile resolution SHALL support only claude at or above the qualified floor (2.1.296), through exactly one maintained profile with an open-ended semver floor and no claude fallback. An observed version below the floor, or unparseable version metadata, SHALL produce an explicit unsupported-version error at tracker resolution naming the observed (or missing) version, the floor, and the migration action (upgrade claude); no detector SHALL be selected for such a session.

#### Scenario: Claude at the floor resolves the maintained profile
- **WHEN** the tracker resolves app `claude_code` with observed version `2.1.296`
- **THEN** resolution selects the maintained claude 2.1.x profile
- **AND THEN** tracked-state reduction proceeds normally

#### Scenario: Claude below the floor raises an unsupported-version error
- **WHEN** the tracker resolves app `claude_code` with observed version `2.1.81`
- **THEN** resolution produces an explicit unsupported-version error naming the observed version and the `2.1.296` floor
- **AND THEN** no claude detector is selected and no tracked state is manufactured for that session

#### Scenario: Unparseable claude version raises an unsupported-version error
- **WHEN** the tracker resolves app `claude_code` with missing or unparseable version metadata
- **THEN** resolution produces the same explicit unsupported-version error surface
- **AND THEN** no fallback detector silently scrapes the surface

### Requirement: Claude profile carries code-side qualified-version metadata
An observed claude version above the qualified floor SHALL resolve to the maintained claude profile silently, without any user-facing warning. The claude registration and profile SHALL carry developer-visible qualified-version metadata (for example, a `qualified_through_version` field or profile note) recording which claude version the profile was qualified against.

#### Scenario: Claude above the qualified floor resolves silently
- **WHEN** the tracker resolves app `claude_code` with observed version `2.1.300`
- **THEN** resolution selects the maintained claude 2.1.x profile without a user-facing warning
- **AND THEN** developer-visible profile metadata records the version the profile was qualified through

### Requirement: Supported TUI profiles derive provider-native pending-input signals

The selected Codex TUI, Claude Code, and Kimi Code profiles SHALL derive a normalized `pending_input` tristate from raw captured snapshot text and profile-owned structural or rendering evidence.

Each profile SHALL scope pending-input evidence to the current live queue/composer surface so historical transcript text does not create a positive result. The profile SHALL emit `unknown` rather than `no` when required structural bounds are missing or ambiguous.

The normalized signal SHALL describe presence only. Provider-specific pending counts MAY remain diagnostic or qualification metadata and SHALL NOT be required in the shared public state.

#### Scenario: Codex queued-follow-up evidence becomes a normalized pending signal

- **WHEN** the selected Codex profile recognizes its bounded current queued-follow-up or pending-input structure
- **THEN** it emits `pending_input=yes`
- **AND THEN** the shared reducer does not need to recover that fact from a provider-specific active reason

#### Scenario: Kimi queue-visible evidence becomes a normalized pending signal

- **WHEN** the selected Kimi profile recognizes its current queue-visible or queued-message structure
- **THEN** it emits `pending_input=yes`
- **AND THEN** stale Kimi transcript prose does not create the same signal

#### Scenario: Complete provider surface without a queue emits no

- **WHEN** a selected supported profile can locate a complete current queue/composer surface and finds no submitted pending instruction
- **THEN** it emits `pending_input=no`
- **AND THEN** it does not require the current turn to be ready before making that negative queue decision

#### Scenario: Multi-prompt queue remains a binary positive

- **WHEN** a selected provider profile observes one, two, or three submitted prompts in the provider-native pending surface
- **THEN** it emits `pending_input=yes` for each supported count
- **AND THEN** the public signal does not vary with provider-specific queue depth

### Requirement: Claude pending-input detection uses the queued composer placeholder

For supported Claude Code profiles, pending-input detection SHALL read the queue state from the current composer's own placeholder payload: `pending_input=yes` when the placeholder carries the bounded queue-editing hint label (`Press up to edit queued messages`), and `pending_input=no` on a complete composer without the hint or on a blocked no-composer surface. The dead queued-preview ghost-cell structure SHALL NOT be used as pending-input evidence.

#### Scenario: Queued placeholder reports pending input

- **WHEN** a Claude turn is active and the composer placeholder payload carries the queue-editing hint label
- **THEN** the selected Claude profile emits `pending_input=yes`
- **AND THEN** the read needs no ghost-cell structure above the composer

#### Scenario: Placeholder-free composer reports no pending input

- **WHEN** the composer is visible with an empty, suggestion, or draft payload and no queue-editing hint
- **THEN** the selected Claude profile emits `pending_input=no`

#### Scenario: Missing composer reports blocked, not unknown

- **WHEN** no Claude composer is visible in the captured surface
- **THEN** the selected Claude profile emits `pending_input=no` along with the other blocked surface booleans
