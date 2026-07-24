## ADDED Requirements

### Requirement: Driver invocation mode is explicit case data
Every behavior-test case or stable variant that originates from a driving-agent prompt SHALL declare `driver_invocation_mode` as `manual` or `automatic`.

`manual` SHALL mean that the driving agent submits an exact prompt containing the intended top-level `$houmao-*` invocation. `automatic` SHALL mean that the driving agent submits natural task context without any `$houmao-*` handle and the oracle evaluates automatic selection or intentional non-selection.

Generated-prompt and lifecycle cases SHALL declare `driver_invocation_mode=not-applicable` with their actual stimulus origin and SHALL NOT be counted as natural-context automatic discovery.

#### Scenario: Manual case invokes a root directly
- **WHEN** a case is classified as manual
- **THEN** its frozen driving stimulus contains the exact intended top-level skill handle
- **AND THEN** the case evaluates direct invocation rather than implicit discovery

#### Scenario: Automatic case supplies only task context
- **WHEN** a case is classified as automatic
- **THEN** its frozen driving stimulus contains no `$houmao-*` handle
- **AND THEN** its oracle names the expected initial root or expected non-selection

#### Scenario: Runtime-generated prompt contains a skill handle
- **WHEN** a maintained prompt generator supplies an explicit agent-entrypoint invocation
- **THEN** the case records generated-prompt stimulus origin and `driver_invocation_mode=not-applicable`
- **AND THEN** the report does not present that attempt as automatic natural-context discovery

### Requirement: Initial selection and downstream delegation have separate oracles
Every resolved case SHALL record `expected_initial_root`, `expected_delegated_roots`, and `expected_route` independently.

An automatic actor-entrypoint case MAY require shared routines or a loop sibling downstream. The report SHALL identify the entrypoint as the initial automatic root and the sibling as delegated execution. It MUST NOT convert observed downstream access into evidence that an explicit-only sibling was directly selected implicitly.

Strict manual welcome cases SHALL name welcome as the initial root only when the driving stimulus contains `$houmao-admin-welcome`. Automatic cases MUST NOT name welcome as an initial or delegated root.

#### Scenario: Automatic operator inspection reaches a shared child
- **WHEN** a natural operator inspection case selects the admin entrypoint and routes to agent inspection
- **THEN** `expected_initial_root` is `houmao-admin-entrypoint`
- **AND THEN** shared routines and the inspect child appear only in the delegated-root and route oracle

#### Scenario: Automatic loop request identifies pro
- **WHEN** a natural request explicitly distinguishes the pro loop and enters through an actor entrypoint
- **THEN** the actor entrypoint is the expected initial root
- **AND THEN** the pro loop is an expected delegated root rather than a directly implicit root

#### Scenario: Automatic informational request stays in the entrypoint
- **WHEN** a natural informational Houmao request selects an actor entrypoint
- **THEN** the delegated-root and operational-route oracles are empty
- **AND THEN** no welcome, shared, or loop sibling may load

#### Scenario: Provider hides initial-root selection
- **WHEN** delegation behavior is observable but reliable initial-root evidence is unavailable
- **THEN** the activation dimension remains `unobservable`
- **AND THEN** the report MAY adjudicate independently observable routing, actor, gate, effect, and outcome dimensions

### Requirement: Invocation-aware selectors compose with functional coverage
The behavior-testing skill SHALL accept `<functional-area>/<manual|automatic>/<coverage-profile>` and `all/<manual|automatic>/<coverage-profile>` selectors in addition to existing area, global, tag, exact-case, exact-variant, and composite forms.

Mode-aware selectors SHALL filter committed cases after cumulative functional-profile expansion and SHALL retain stable catalog order and deduplication. Existing `<functional-area>/<coverage-profile>` and `all/<coverage-profile>` selectors SHALL include every invocation mode in that functional slice, including applicable generated-prompt and lifecycle cases.

Unknown invocation modes or malformed selector forms MUST fail before provider launch.

#### Scenario: Maintainer selects automatic normal activation cases
- **WHEN** the maintainer selects `activation/automatic/normal`
- **THEN** the skill resolves only automatic activation cases introduced at minimal or normal
- **AND THEN** manual, generated-prompt, and lifecycle cells are excluded

#### Scenario: Maintainer selects complete functional coverage
- **WHEN** the maintainer selects `all/complete`
- **THEN** the selection includes every committed case and variant regardless of invocation mode
- **AND THEN** the report retains invocation-mode attribution for each resolved cell

#### Scenario: Composite mode selectors overlap
- **WHEN** a maintainer combines a mode-aware selector with an exact case already included by that selector
- **THEN** the case appears once in stable catalog order
- **AND THEN** every contributing selector is frozen in the run manifest

### Requirement: Version 3 adds automatic entrypoint and delegation cases
The behavior catalog SHALL advance to `houmao-dev-behavior-cases.v3`, contain 46 stable case records before matrix expansion, and add `ACT-005`, `ACT-006`, `SHR-009`, and `LOOP-008`.

`ACT-005` SHALL have informational and operational managed-agent variants. The informational variant SHALL expect agent-entrypoint selection without identity verification or delegation. The operational variant SHALL expect fresh identity verification before delegation. `ACT-006` SHALL use raw-operator and genuine-managed variants in an explicitly combined-pack home to cover actor-context disambiguation. `SHR-009` SHALL use admin and managed-agent variants to cover natural actor-entrypoint selection followed by shared-child delegation. `LOOP-008` SHALL use admin-pro and agent-lite variants to cover natural actor-entrypoint selection followed by delegation to an explicitly distinguished loop sibling.

`ACT-001`, `ACT-003`, `ADM-002`, and `LOOP-001` SHALL advance to revision 2:

- `ACT-001` SHALL expect the admin entrypoint to answer its natural first-use Houmao question locally and MAY recommend manual welcome; welcome activation or delegation is forbidden.
- `ACT-003` SHALL move to minimal and expect admin-entrypoint selection followed by the inspect route.
- `ADM-002` SHALL expect an empty explicit admin-entrypoint invocation to return local read-only guidance and a manual welcome recommendation without delegation.
- `LOOP-001` SHALL distinguish permissible admin-entrypoint selection from forbidden automatic pro or lite selection.

Every other existing case SHALL preserve its id, revision, exact stimulus, and semantic oracle. Existing explicit welcome cases SHALL remain the manual activation coverage for welcome.

#### Scenario: Minimal activation coverage is resolved
- **WHEN** the maintainer selects `activation/minimal`
- **THEN** the result includes natural admin informational activation, unrelated-task non-activation, natural admin operational activation, and natural managed informational and operational activation variants
- **AND THEN** the activation area contains four cumulative minimal case records before variant expansion

#### Scenario: Informational managed phase is qualified
- **WHEN** the informational `ACT-005` variant runs
- **THEN** the agent entrypoint is expected as the initial root
- **AND THEN** identity verification, sibling loading, and operational mutation are forbidden

#### Scenario: Operational managed phase is qualified
- **WHEN** the operational `ACT-005` variant runs
- **THEN** the agent entrypoint is expected as the initial root
- **AND THEN** exact fresh identity verification is required before delegation

#### Scenario: Manual welcome activation is qualified
- **WHEN** the existing `ACT-004/admin-welcome` variant runs
- **THEN** its explicit `$houmao-admin-welcome` stimulus selects welcome directly
- **AND THEN** no automatic welcome claim is made

#### Scenario: Natural shared routing is qualified
- **WHEN** either `SHR-009` actor variant runs
- **THEN** the matching actor entrypoint is expected first
- **AND THEN** the request delegates to the intended shared child with the correct immutable actor frame
- **AND THEN** direct implicit shared-root selection is forbidden

#### Scenario: Combined-pack actor context is qualified
- **WHEN** either `ACT-006` context variant runs from an explicitly combined-pack home
- **THEN** raw operator context expects the admin entrypoint and genuine managed context expects the agent entrypoint
- **AND THEN** prompt wording alone cannot select the opposite actor entrypoint

#### Scenario: Natural explicit loop choice is qualified
- **WHEN** either `LOOP-008` actor and loop variant runs
- **THEN** the matching actor entrypoint is expected first
- **AND THEN** the explicitly distinguished loop sibling receives the inherited actor frame
- **AND THEN** the other loop and direct implicit loop selection are forbidden

### Requirement: Version 3 cumulative profile counts are deterministic
Before matrix expansion, version 3 SHALL resolve cumulative global counts of 13 minimal, 25 normal, 45 extended, and 46 complete case records.

Per-area cumulative counts SHALL be activation `4/5/6/6`, managed bootstrap `1/1/2/2`, admin entrypoint `1/3/8/9`, agent entrypoint `1/3/9/9`, shared routines `2/5/9/9`, agent loops `3/6/8/8`, and generated prompts `1/2/3/3`.

Coverage profile selection MUST remain independent of provider selection, repetition count, invocation-mode filtering, and stable variant expansion.

#### Scenario: Normal global coverage is resolved
- **WHEN** the maintainer selects `all/normal`
- **THEN** the catalog resolves exactly 25 committed case records before matrix expansion
- **AND THEN** provider, repetition, and variant choices do not alter that semantic membership

#### Scenario: Complete global coverage is resolved
- **WHEN** the maintainer selects `all/complete`
- **THEN** the catalog resolves all 46 committed case records and every declared stable variant
- **AND THEN** completeness is scoped to catalog version 3

### Requirement: Run artifacts and reports preserve invocation provenance
Before provider launch, the frozen run manifest SHALL record requested selectors, catalog version and digest, resolved cases and variants, driver invocation mode, stimulus origin, exact stimulus digest, expected initial root, expected delegated roots, expected route, providers, contexts, and repetitions.

Reports SHALL separate manual results, automatic positive-selection results, automatic intentional-non-selection results, and non-driver-origin results. Automatic informational and operational phase results SHALL be distinguishable. A report MUST NOT claim automatic entrypoint qualification when the driver supplied an explicit skill handle or when initial-root evidence remained unobservable.

#### Scenario: Automatic activation is fully observable
- **WHEN** all required automatic attempts expose reliable matching initial-root evidence and pass their other required dimensions
- **THEN** the report may state that automatic selection was qualified for those cases
- **AND THEN** it links initial-root, phase, identity, and downstream delegation evidence separately where applicable

#### Scenario: Automatic behavior passes without root evidence
- **WHEN** observable behavior passes but initial-root selection is unavailable
- **THEN** the aggregate remains behavior-pass-activation-unobserved under the existing verdict contract
- **AND THEN** the invocation-mode summary does not count it as fully qualified automatic activation

### Requirement: Structural validation enforces invocation constraints
Focused repository tests SHALL validate catalog version, case ids, case revisions, cumulative counts, selector documentation, and exactly one driver invocation mode per resolved case or variant.

The tests SHALL reject automatic driver stimuli containing `$houmao-*`, manual driver stimuli that omit their intended top-level handle, `not-applicable` modes outside generated-prompt or lifecycle origins, automatic welcome initial or delegated roots, and initial-root or delegated-root oracles that contradict packaged activation policy.

Semantic-preservation coverage SHALL compare all unchanged version 2 cases while allowing only the four declared version 3 additions and the `ACT-001`, `ACT-003`, `ADM-002`, and `LOOP-001` revision-2 oracle changes.

#### Scenario: Automatic case accidentally names a skill handle
- **WHEN** a committed automatic driver stimulus contains `$houmao-admin-entrypoint`, `$houmao-agent-entrypoint`, or another `$houmao-*` handle
- **THEN** structural validation fails before a live run can be planned

#### Scenario: Automatic case expects welcome
- **WHEN** an automatic case declares welcome as its initial or delegated root
- **THEN** structural validation fails
- **AND THEN** welcome coverage must use a manual stimulus containing `$houmao-admin-welcome`

#### Scenario: Explicit-only root is declared as an automatic initial root
- **WHEN** a case declares shared routines or either loop as an automatic initial root
- **THEN** structural validation fails
- **AND THEN** the case must instead name an actor entrypoint first or become a manual case

#### Scenario: Existing case changes without revision
- **WHEN** a version 2 case outside the declared revision-2 set changes its exact stimulus or semantic oracle
- **THEN** semantic-preservation validation fails
