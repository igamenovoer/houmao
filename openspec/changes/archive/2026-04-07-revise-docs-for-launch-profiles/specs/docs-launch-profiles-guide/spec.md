## ADDED Requirements

### Requirement: Launch-profiles conceptual guide exists

The getting-started section SHALL include a page at `docs/getting-started/launch-profiles.md` that explains the shared launch-profile semantic model and the two user-facing authoring lanes.

The page SHALL explain:

- what a launch profile IS: reusable, operator-owned, birth-time launch configuration that is distinct from reusable source definitions and distinct from live managed-agent instances,
- the two authoring lanes: easy `profile` (specialist-backed, opinionated) and explicit `launch-profile` (recipe-backed, low-level),
- the shared catalog-backed model that backs both lanes,
- the five-layer effective-launch precedence order,
- prompt overlay modes (`append` and `replace`) and where overlay composition happens relative to backend-specific role injection,
- how launch-profile provenance flows into runtime metadata and is reported by inspection commands,
- when to use which lane.

The page SHALL link to:

- `docs/getting-started/easy-specialists.md` for the easy lane operator workflow,
- `docs/getting-started/agent-definitions.md` for the recipe authoring path and the `.houmao/agents/` projection layout,
- `docs/reference/cli/houmao-mgr.md` for the canonical CLI surfaces,
- `docs/reference/build-phase/launch-overrides.md` for how launch-profile defaults compose with launch overrides during build.

The page SHALL be derived from the active spec capabilities `agent-launch-profiles`, `houmao-mgr-project-easy-cli`, `houmao-mgr-project-agents-launch-profiles`, `houmao-mgr-agents-launch`, `brain-launch-runtime`, and `project-config-catalog`.

The page SHALL NOT introduce CLI shapes, env vars, or precedence behavior that are not present in those active spec capabilities.

#### Scenario: Reader understands what a launch profile is

- **WHEN** a reader opens the launch-profiles guide for the first time
- **THEN** they find a clear explanation that a launch profile is reusable birth-time launch configuration
- **AND THEN** they understand it is distinct from reusable source definitions (specialists and recipes) and distinct from live managed-agent instances
- **AND THEN** they understand that persisting, listing, inspecting, or removing a launch profile does not by itself create, stop, or mutate a live instance

#### Scenario: Reader understands the easy-versus-explicit lane split

- **WHEN** a reader scans the launch-profiles guide for the two user-facing surfaces
- **THEN** they find that the easy lane uses `project easy profile ...` and is specialist-backed
- **AND THEN** they find that the explicit lane uses `project agents launch-profiles ...` and is recipe-backed
- **AND THEN** they find that both lanes write into one shared catalog-backed launch-profile object family

### Requirement: Launch-profiles guide documents the precedence chain

The launch-profiles guide SHALL document the effective-launch precedence chain as the following ordered layers:

1. tool-adapter defaults
2. source recipe defaults
3. launch-profile defaults
4. direct CLI overrides
5. live runtime mutations

The guide SHALL state that fields omitted by a higher-priority layer survive from the next lower-priority layer.

The guide SHALL state that live runtime mutations such as late mailbox registration remain runtime-owned and SHALL NOT rewrite the stored launch profile.

The guide SHALL state that direct launch-time overrides such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir` do not rewrite the stored launch profile.

The guide SHALL render this precedence model as a mermaid diagram, not as ASCII art.

#### Scenario: Reader sees the five-layer precedence model

- **WHEN** a reader checks the launch-profiles guide for how launch-time inputs combine
- **THEN** the page lists the five layers in order
- **AND THEN** the page explains that direct CLI overrides win over the launch profile but do not rewrite it

#### Scenario: Reader sees a mermaid precedence diagram

- **WHEN** a reader scrolls to the precedence section of the launch-profiles guide
- **THEN** the precedence chain is rendered as a mermaid fenced code block
- **AND THEN** the page does not represent the precedence chain as plain-text ASCII art

### Requirement: Launch-profiles guide documents prompt overlays

The launch-profiles guide SHALL document the supported prompt overlay modes:

- `append` SHALL be defined as appending profile-owned prompt text after the source role prompt,
- `replace` SHALL be defined as replacing the source role prompt with profile-owned prompt text.

The guide SHALL state that the effective role prompt is composed before backend-specific role injection planning begins, and that the runtime SHALL NOT reapply the overlay as a separate second bootstrap step on resumed turns.

The guide SHALL state that prompt overlay payloads are stored as managed file-backed content and that the catalog stores only the references to those payloads.

#### Scenario: Reader understands append versus replace overlays

- **WHEN** a reader opens the prompt-overlay section of the launch-profiles guide
- **THEN** the page distinguishes `append` and `replace`
- **AND THEN** the page states that overlay composition happens before backend-specific role injection
- **AND THEN** the page states that resumed turns do not replay the overlay as a separate bootstrap step

### Requirement: Launch-profiles guide documents profile provenance reporting

The launch-profiles guide SHALL state that the build manifest and runtime launch metadata preserve, in secret-free form:

- whether the launch originated from a specialist source or a recipe source,
- whether the birth-time reusable config came from an easy profile or an explicit launch profile,
- the originating profile name when available.

The guide SHALL state that easy `instance list` and `instance get` report the originating easy-profile identity when runtime-backed state makes it resolvable, and that the same lane and profile information appears on inspection commands for explicit launch-profile-backed managed agents.

#### Scenario: Reader understands how profile provenance shows up on inspection

- **WHEN** a reader opens the provenance section of the launch-profiles guide
- **THEN** the page explains that managed-agent inspection reports both the source lane (specialist or recipe) and the birth-time lane (easy profile or explicit launch profile)
- **AND THEN** the page explains that the inspection output does not expose secret credential values inline

### Requirement: Launch-profiles guide compares the source and birth-time object families

The launch-profiles guide SHALL include a comparison that distinguishes:

- specialists (easy lane source definitions),
- recipes (explicit lane source definitions),
- easy profiles (specialist-backed reusable birth-time configuration),
- explicit launch profiles (recipe-backed reusable birth-time configuration),
- runtime `LaunchPlan` (derived, ephemeral, runtime-owned),
- live managed-agent instances (running runtime objects).

The comparison SHALL state which of those objects are user-authored, which are stored in the catalog, which are projected into `.houmao/agents/`, and which are derived only at launch time.

#### Scenario: Reader can place every object in the source-versus-birth-time taxonomy

- **WHEN** a reader checks the comparison section of the launch-profiles guide
- **THEN** they find that specialists and recipes are user-authored source definitions
- **AND THEN** they find that easy profiles and explicit launch profiles are user-authored birth-time configuration that share one underlying catalog model
- **AND THEN** they find that the runtime `LaunchPlan` is derived and ephemeral and is not user-authored
