# docs-launch-profiles-guide Specification

## Purpose

Define the documentation requirements for the shared launch-profiles conceptual guide in the getting-started section. The guide explains the operator-owned launch-profile semantic model, the two authoring lanes (easy specialist-backed and explicit recipe-backed), the shared catalog-backed object family, the five-layer effective-launch precedence chain, prompt overlay composition, and launch-profile provenance reporting.
## Requirements
### Requirement: Launch-profiles conceptual guide exists

The getting-started section SHALL include a page at `docs/getting-started/launch-profiles.md` that explains the shared launch-profile semantic model and the two user-facing authoring lanes.

The page SHALL explain:

- what a launch profile IS: reusable, operator-owned, birth-time launch configuration that is distinct from reusable source definitions and distinct from live managed-agent instances,
- the two authoring lanes: easy `profile` (specialist-backed, opinionated) and explicit `launch-profile` (recipe-backed, low-level),
- the shared catalog-backed model that backs both lanes,
- the five-layer effective-launch precedence order,
- prompt overlay modes (`append` and `replace`) and where overlay composition happens relative to backend-specific role injection,
- that launch profiles may store a gateway mail-notifier appendix default as birth-time launch configuration,
- that explicit `project agents launch-profiles ...` and easy `project easy profile ...` authoring lanes both support that stored notifier appendix default,
- that launch-time materialization seeds that stored appendix into runtime gateway notifier state for the launched session,
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

#### Scenario: Reader understands notifier appendix defaults as launch-owned config

- **WHEN** a reader studies the launch-profiles guide for gateway-related launch defaults
- **THEN** the page explains that launch profiles may store a gateway mail-notifier appendix default
- **AND THEN** it explains that launch-time materialization seeds that appendix into runtime gateway notifier state rather than enabling notifier polling by itself

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

### Requirement: Launch-profiles guide documents the managed prompt header
The launch-profiles guide SHALL document the Houmao-managed prompt header as part of effective launch-prompt composition.

The guide SHALL explain:
- that managed launches prepend a general Houmao-managed header by default,
- that the header identifies the managed agent and points the agent toward `houmao-mgr` plus supported Houmao system interfaces for Houmao-related work,
- that the header is composed after launch-profile prompt overlay resolution and before backend-specific prompt injection,
- that launch-time override can disable or force the header,
- that stored launch-profile policy can explicitly enable, disable, or inherit the header behavior.

The guide SHALL state that the managed header remains general-purpose and does not rely on naming individual packaged guidance entries.

#### Scenario: Reader understands where the managed header fits in launch-prompt composition
- **WHEN** a reader opens the launch-profiles guide to understand launch-prompt behavior
- **THEN** the page explains that prompt overlay resolution happens before managed-header prepend
- **AND THEN** the page explains that backend-specific prompt injection sees one composed effective launch prompt

#### Scenario: Reader can find the managed-header opt-out story
- **WHEN** a reader looks for how to disable the managed prompt header
- **THEN** the guide explains the launch-time override and stored launch-profile policy surfaces
- **AND THEN** it explains that unset policy falls back to the default enabled behavior

### Requirement: Launch-profiles guide distinguishes overrides, patches, and replacements
The launch-profiles guide SHALL distinguish:

- direct launch-time overrides, which affect only one launch and do not rewrite stored launch profiles,
- profile patch commands, which mutate stored reusable defaults while preserving unspecified fields,
- profile replacement commands, which rewrite the same named profile in the same lane and clear omitted optional fields.

The guide SHALL explain that the easy and explicit lanes share one catalog-backed launch-profile family but replacement remains lane-bounded.

#### Scenario: Reader can choose patch versus replacement
- **WHEN** a reader wants to change one stored reusable launch default
- **THEN** the launch-profiles guide directs them to use the appropriate patch command for their lane
- **AND THEN** the guide reserves same-name `create --yes` or `add --yes` for full same-lane replacement

#### Scenario: Reader understands direct launch overrides do not persist
- **WHEN** a reader compares launch-time overrides with stored profile edits
- **THEN** the guide states that direct launch-time overrides affect only the submitted launch
- **AND THEN** the guide states that profile `set` changes future launches from the stored profile

### Requirement: Launch-profiles guide documents managed-header section policy
The launch-profiles guide SHALL document that stored launch profiles can persist managed-header section policy independently from whole managed-header policy.

At minimum, the guide SHALL explain:

- `identity`, `houmao-runtime-guidance`, and `automation-notice` default to enabled when the whole managed header is enabled,
- `task-reminder` and `mail-ack` default to disabled unless explicitly enabled,
- whole-header `--no-managed-header` disables every section,
- section-level policy can disable one section such as `automation-notice` while keeping the identity and Houmao runtime guidance sections,
- section-level policy can enable a default-disabled section such as `task-reminder` or `mail-ack`,
- omitted section policy means section default rather than always enabled or disabled,
- direct launch section overrides affect only one launch and do not rewrite stored launch-profile state.

#### Scenario: Reader understands stored section policy
- **WHEN** a reader opens the launch-profiles guide
- **THEN** the guide explains how stored managed-header section policy works
- **AND THEN** the guide states that omitted section policy falls back to each section's default
- **AND THEN** the guide states that `task-reminder` and `mail-ack` default disabled unless explicitly enabled

#### Scenario: Reader understands whole-header policy precedence
- **WHEN** a reader opens the launch-profiles guide
- **THEN** the guide explains that whole-header disable suppresses all managed-header sections
- **AND THEN** the guide distinguishes whole-header policy from section-level policy

#### Scenario: Reader understands direct override scope
- **WHEN** a reader opens the launch-profiles guide
- **THEN** the guide explains that direct launch section overrides affect only the current launch
- **AND THEN** the guide states that direct launch overrides do not rewrite stored profile policy

### Requirement: Launch-profiles guide documents memo seeds
The launch-profiles guide SHALL document memo seeds as optional launch-profile-owned birth-time initialization for `houmao-memo.md` and `pages/`.

The guide SHALL use memo terminology for this feature, including `memo seed`, `--memo-seed-text`, `--memo-seed-file`, and `--memo-seed-dir`. It SHALL NOT call this feature a memory seed.

The guide SHALL explain:
- supported seed sources: inline text, Markdown file, and memo-shaped directory,
- accepted directory shape: `houmao-memo.md` and `pages/`,
- that memo seeds do not expose an apply policy,
- that memo seeds replace only managed-memory components represented by the seed source,
- that memo-only seeds update `houmao-memo.md` without clearing pages,
- that a directory seed containing `pages/` replaces the contained pages tree,
- that an empty `pages/` directory in a seed clears pages while leaving memo unchanged when `houmao-memo.md` is omitted,
- that `--clear-memo-seed` removes stored profile seed configuration rather than seeding an empty memo,
- that prompt overlays remain prompt shaping while memo seeds materialize durable memo/page content before launch.

#### Scenario: Reader finds memo seed terminology
- **WHEN** a reader opens the launch-profiles guide
- **THEN** the page describes the feature as memo seeds
- **AND THEN** the page does not introduce the term memory seed for this feature
- **AND THEN** the page does not document `--memo-seed-policy`

#### Scenario: Reader understands memo seed versus prompt overlay
- **WHEN** a reader compares prompt overlays and memo seeds
- **THEN** the guide states that prompt overlays affect launch prompt composition
- **AND THEN** the guide states that memo seeds write represented `houmao-memo.md` and contained `pages/` content before provider startup

#### Scenario: Reader understands memo-only seeds
- **WHEN** a reader checks memo seed behavior for `--memo-seed-text "note"`
- **THEN** the guide states that the launch replaces `houmao-memo.md`
- **AND THEN** the guide states that the launch does not clear existing pages

