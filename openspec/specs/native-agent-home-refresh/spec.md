# Native Agent Home Refresh Specification

## Purpose

Expose an active managed agent's native home, inspect skills/MCP freshness independently of update ownership, and request native refresh while preserving the running agent and the separate manifest-backed relaunch boundary.

## Requirements


### Requirement: Common Plugin Observation Has an Explicit Resource Boundary

The common contract SHALL cover skills and MCP as `common-plugin`. Agent-specific extensions outside those forms SHALL be `native-special-plugin`, with no common inventory or freshness API. Classification SHALL follow exposed resources rather than installation packaging. Existing Houmao gateway-plugin management SHALL remain separate.

#### Scenario: Native Extension Contributes a Common Resource
- **WHEN** an agent-native extension contributes a skill or MCP server
- **THEN** its exposed common resource participates in the common view under the qualified adapter's coverage
- **AND** Houmao does not claim to inventory or verify the extension package itself

#### Scenario: Caller Seeks Native Extension Inventory
- **WHEN** a caller inspects the common-plugin interface for an agent with native-specific extensions
- **THEN** the response identifies its skills/MCP scope without presenting a common native-special-plugin inventory
- **AND** native extension inspection remains the caller's native workflow

### Requirement: DSH Is Primary and Other Maintained Bodies Are Best Effort

DSH headless, service, and Web SHALL be primary acceptance targets. Each mode SHALL report its own observed or qualified native read boundary. Kimi Code, Codex, and Claude Code SHALL receive best-effort investigation and support for every qualified path available through maintained controls. Secondary limitations SHALL remain explicit per resource without blocking DSH acceptance. Pi SHALL remain postponed.

#### Scenario: Secondary Body Supports Only Part of the Common Scope
- **WHEN** a maintained secondary body has verified skill refresh but unqualified MCP refresh
- **THEN** capability reporting preserves the positive skill capability and explicit MCP limitation
- **AND** the incomplete coverage does not establish full common freshness or block DSH acceptance

#### Scenario: Native Capability Has No Maintained Transport
- **WHEN** an installed body exposes native reload through a channel its maintained Houmao backend does not own
- **THEN** the adapter reports the actual transport limitation rather than advertising managed live refresh
- **AND** it does not initiate an unqualified backend or start a replacement body to obtain that channel

#### Scenario: A persistent service remains live after a home edit

- **WHEN** a DSH service consumes the affected resource only on session initialization
- **THEN** a second prompt on the same connection does not establish refreshed state and inspection or refresh never implicitly relaunches it

### Requirement: Native Home Inspection Identifies the Active Agent Home

Home inspection SHALL report the resolved native home, its selector variable when known, and the selected active agent identity. It SHALL use current runtime authority without guessing from the caller's operating-system home, changing home contents, or starting execution. An active headless envelope between workers SHALL remain inspectable.

#### Scenario: Native Home Differs From the Caller Home
- **WHEN** an operator inspects an agent whose native home is `/runtime/worker-home` while the caller's home is `/home/operator`
- **THEN** the result identifies `/runtime/worker-home` and the selected agent
- **AND** it does not substitute the caller's home, project worktree, or session-artifact directory

#### Scenario: Headless Worker Is Between Turns
- **WHEN** an active managed headless envelope has no currently running provider worker
- **THEN** home inspection reports its authoritative native home without creating a worker or conversation

#### Scenario: Home Authority Is Unknown
- **WHEN** a target has no verified native-home selection in its active runtime
- **THEN** inspection returns an explicit unsupported or unavailable result without selecting an ambient home

#### Scenario: Inspection Leaves Private Material Unread
- **WHEN** an authorized caller inspects a native home containing credentials
- **THEN** the home descriptor reports no configuration contents, credential values, or environment dump
- **AND** home inspection leaves that material unread and unchanged

### Requirement: Current Common Material Can Come From Any Writer

Observation and refresh SHALL use the selected agent's current effective native skill/MCP inputs, regardless of editor, installer, shell, agent tool, or native harness. They SHALL NOT require a Houmao installation receipt, install packages, update a harness, accept replacement content, or restore caller-owned files from a saved inventory.

#### Scenario: Operator Updates Home With External Tooling
- **WHEN** an operator adds, updates, and removes skill/MCP material outside Houmao
- **THEN** observation and refresh evaluate the resulting native inputs without requiring a Houmao update receipt

#### Scenario: Harness Updates Its Own Skills
- **WHEN** the native harness updates its skills before a Houmao observation or refresh
- **THEN** Houmao uses the same common contract as for operator-authored changes
- **AND** it does not restore a prior source snapshot

#### Scenario: Request Supplies Installation Instructions
- **WHEN** a refresh request supplies package sources, desired revisions, replacement skill/MCP definitions, or arbitrary commands
- **THEN** strict validation rejects the request before applying its supplied content

### Requirement: Refresh Does Not Reapply Houmao Launch Configuration

Observation and refresh SHALL use runtime metadata for authority and control without rebuilding a home, resolving edited Houmao launch profiles, reprojecting brain configuration, generating system prompts, or resynchronizing installed skills. Missing or invalid materialized inputs SHALL remain explicit failures instead of triggering manifest-backed repair.

#### Scenario: Launch Profile Prompt Changes After Launch
- **WHEN** an operator edits a Houmao launch profile contributing a generated system prompt and requests refresh
- **THEN** Houmao leaves the materialized launch-derived prompt unchanged and does not apply the edited profile

#### Scenario: Native Configuration Was Edited Manually
- **WHEN** effective native skill/MCP configuration differs from its launch projection
- **THEN** observation and refresh use current native inputs under native precedence
- **AND** Houmao does not restore the old projection before reload or a later headless invocation

#### Scenario: Materialized Input Is Missing
- **WHEN** a required materialized native file has been removed
- **THEN** the applicable native validation or availability failure remains explicit
- **AND** Houmao does not recreate it from a launch manifest

### Requirement: Common Freshness Uses Evidence and Explicit Unknown State

Common observations SHALL identify scope, completeness, time, execution identity, native boundary, and per-resource `current`, `pending`, or `unknown` freshness. Aggregate current SHALL require complete common coverage and evidence for every required component. Native names, timestamps, connection health, or a prior Houmao receipt alone SHALL NOT establish freshness.

#### Scenario: Skill Catalog Is Cached
- **WHEN** the native skill list is complete for its cached revision but has no evidence covering current external edits
- **THEN** the observation reports pending where a mismatch is known or unknown where comparison is unavailable
- **AND** cached completeness does not establish current whole-scope freshness

#### Scenario: MCP Process Remains Connected After an External Upgrade
- **WHEN** an MCP package changes while its configured command and existing connection remain unchanged
- **THEN** the observation does not infer that the running server loaded the new implementation
- **AND** unverified implementation freshness remains unknown even if declaration freshness is current

#### Scenario: Common Scope Is Authoritatively Empty
- **WHEN** complete native evidence establishes that no effective skills or MCP entries are configured
- **THEN** the empty common scope can be current
- **AND** an incomplete or unavailable inventory cannot be treated as empty

#### Scenario: Input Changes During Observation
- **WHEN** relevant inputs or execution identity change before a source/runtime comparison can be confirmed
- **THEN** the result exposes superseded or unknown evidence rather than claiming one stable latest snapshot

#### Scenario: Native Revision Is Available
- **WHEN** the body supplies an applied revision or resource generation with a known scope
- **THEN** the observation preserves that native evidence
- **AND** missing native revisions are not replaced with fabricated installed generations

### Requirement: Common Observation Is Read Only and Owner Bound

Common state queries SHALL report qualified skills/MCP capabilities, effective inventory coverage, freshness, boundaries, safe evidence, and health for the bound agent. They SHALL NOT initiate invalidation, forced rescans, native reload, worker startup, or model turns. Autonomous native discovery SHALL remain allowed. Private bodies, credentials, and raw configuration SHALL remain excluded.

#### Scenario: Operator Inspects State During Native Automatic Activity
- **WHEN** a caller reads common state while a native watcher independently applies an update
- **THEN** the query reports the observed state and any incomplete or superseded evidence without taking ownership of that update

#### Scenario: Only a Forced Rescan Can Establish Current State
- **WHEN** the body offers a catalog force-rescan operation but insufficient passive freshness evidence
- **THEN** the query preserves unknown freshness
- **AND** it does not execute the rescan while presenting the request as read-only

#### Scenario: Health and Freshness Differ
- **WHEN** a current MCP declaration is applied but its endpoint is unreachable
- **THEN** the result retains declaration freshness and connection health as distinct facts
- **AND** connection failure is not misreported as proof that the declaration is stale

### Requirement: Native Automatic Updates Are First Class

The contract SHALL accept native automatic discovery and refresh independently of Houmao triggers. Common freshness SHALL describe observed native state, not which caller caused the update. Houmao SHALL NOT require all native updates to pass through gateway admission or disable qualified automatic behavior merely to retain trigger ownership.

#### Scenario: Native Watcher Already Applied the Update
- **WHEN** external skill/MCP edits were applied by the body before Houmao queried them
- **THEN** the observation reports confirmed current state using the same evidence rules as a Houmao-triggered update

#### Scenario: Update Has No Houmao Operation Record
- **WHEN** the body applies a common update without a Houmao refresh receipt
- **THEN** receipt absence alone does not make the resource stale or unsupported

#### Scenario: Native Update Races a Managed Reload
- **WHEN** native automatic behavior changes common state during a Houmao-triggered reload
- **THEN** the adapter uses qualified native coordination or reports the resulting evidence limitations
- **AND** it does not claim exclusive control of every native mutation

### Requirement: Manual Refresh Observes Before Choosing a No Op

Manual refresh SHALL observe common-plugin state before selecting an action. It SHALL return `method=noop` and `outcome=already_current` only for confirmed complete current coverage, without initiating reload or worker/model work. Pending or unknown state SHALL NOT be silently converted into that result.

#### Scenario: Automatic Update Makes Manual Refresh Redundant
- **WHEN** observation confirms that native automatic behavior already made the complete common scope current
- **THEN** manual refresh returns already-current with no native refresh mutation

#### Scenario: Only Skills Are Known Current
- **WHEN** skills are current but MCP freshness is pending or unknown
- **THEN** manual refresh preserves the distinct states and does not claim an already-current whole-scope no-op

#### Scenario: Unknown State Has a Qualified Refresh Path
- **WHEN** freshness cannot be established passively but a safe native refresh path is qualified
- **THEN** manual refresh can attempt that path and observe again
- **AND** it does not substitute an unsupported already-current claim

### Requirement: Automatic Discovery Retains Its Future Native Boundary

A qualified automatic strategy SHALL initiate no native mutation, provider worker, or model turn. It SHALL be preferred when it covers remaining common resources and SHALL report `next_step`, `next_turn`, or `next_load` as applicable. Future discovery SHALL remain distinct from an already-current observation and ordinary later execution SHALL consume current native inputs.

#### Scenario: Headless Resources Are Read on the Next Invocation
- **WHEN** a qualified headless envelope receives refresh between ordinary prompts
- **THEN** refresh reports its automatic next-turn behavior without starting a worker
- **AND** it does not fabricate observations of a live worker that does not exist

#### Scenario: Skill Body Is Read on Demand
- **WHEN** native behavior rereads a changed skill body at its next load
- **THEN** refresh identifies next-load availability without claiming that the model already reread it

#### Scenario: Automatic Refresh Is Requested During a Turn
- **WHEN** a qualified automatic strategy covers later common-resource discovery during active work
- **THEN** it can return immediately without modifying, interrupting, or replaying that work

#### Scenario: Earlier Skill Instructions Remain in History
- **WHEN** a revised skill becomes available after an older body was loaded
- **THEN** the original conversation history remains intact
- **AND** freshness does not claim removal or replacement of earlier tool results

### Requirement: Native Refresh Can Have Broader Nonatomic Effects

A qualified native refresh SHALL be permitted to reload native-special-plugin and other native configuration as normal effects. It SHALL NOT require common-only effects or all-or-nothing application. Native completion, partial effects, common freshness, and readiness SHALL remain distinct. There SHALL be no common inventory or freshness guarantee for those broader extensions.

#### Scenario: Native Reload Updates Common and Special Plugins
- **WHEN** the body's supported reload refreshes skills/MCP and agent-native extensions together
- **THEN** Houmao permits that operation subject to its no-restart and admission contracts
- **AND** it verifies the common scope without promising that only common resources changed

#### Scenario: Native Host Code Remains Pending
- **WHEN** a native operation applies skills/MCP but reports unrelated host or native-special-plugin code pending until restart
- **THEN** confirmed current common resources remain current
- **AND** that pending diagnostic alone does not turn the common result into restart-required

#### Scenario: Native Replacement Fails Outside the Common Scope
- **WHEN** a broader extension fails to reload but common freshness and native readiness are independently confirmed
- **THEN** the common result remains based on that evidence and retains a safe native failure diagnostic
- **AND** it does not claim that every native extension refreshed successfully

#### Scenario: Native Failure Impairs Common Resources
- **WHEN** a broader native failure prevents MCP/skill activation or leaves readiness uncertain
- **THEN** the result exposes the affected common failure or uncertainty rather than hiding it outside the common scope

### Requirement: Refresh Never Restarts or Replaces the Agent Execution

Refresh SHALL NOT restart or replace the harness process, respawn a managed surface, activate a cold agent, choose another conversation, invoke relaunch, or call a native host-exit/restart hook. Common changes known to require restart SHALL retain `restart_required` without a restart fallback. Internal plugin/resource or MCP subprocess reload SHALL preserve the running agent and conversation.

#### Scenario: A Common Resource Requires Process Restart
- **WHEN** a common resource cannot become current without restarting the harness
- **THEN** refresh reports that limitation and any already-applied resource outcomes
- **AND** the agent stays running for the caller's separate explicit relaunch choice

#### Scenario: Restart Requirement Follows Partial Application
- **WHEN** native refresh applies some common changes and then establishes that another common change needs restart
- **THEN** the result preserves both the applied effects and the restart-required remainder
- **AND** it does not describe the whole operation as having made no changes

#### Scenario: Caller Requests Forced Restart
- **WHEN** a refresh request supplies force or restart fields/options
- **THEN** validation rejects the request before native effects

#### Scenario: Native Source Watch Path Can Exit the Host
- **WHEN** a candidate native refresh path invokes a host exit/restart hook
- **THEN** that path is not advertised or used as Houmao refresh
- **AND** another qualified non-restarting path or an explicit limitation is reported

#### Scenario: Native Reload Rebuilds Internal Resources
- **WHEN** native refresh rebuilds plugin resources or reconnects an MCP subprocess
- **THEN** successful refresh retains the existing harness process and bound conversation

### Requirement: Live Managed Reload Requires Immediate Native Admission

Houmao-initiated live reload SHALL claim a safe native boundary and recheck captured identity before mutation. Busy, pending-input, interaction-blocked, or uncertain boundaries SHALL be refused immediately without interruption, idle waiting, or queueing. The guard SHALL cover affected shared/child execution without claiming to govern independent native automatic updates.

#### Scenario: Calling Agent Is Inside Its Active Turn
- **WHEN** an agent tool call requests a mutating reload while its own work prevents admission
- **THEN** refresh returns busy without waiting for that same turn to finish or scheduling deferred work

#### Scenario: Browser Starts Work Before Native Admission
- **WHEN** a browser starts a turn after gateway observation but before native reload admission
- **THEN** the native boundary refuses the managed reload and preserves the browser turn

#### Scenario: Input Arrives During Native Maintenance
- **WHEN** managed refresh owns native maintenance and new input seeks to start affected execution
- **THEN** no affected execution begins before maintenance safely settles
- **AND** ordinary gateway notifications are refused without deferred storage

#### Scenario: Child Execution Shares Resources
- **WHEN** a child or another live execution shares resources affected by the native operation
- **THEN** managed reload is busy or unsupported unless the backend can establish admission for the affected scope

#### Scenario: Passive No Op Is Safe During Active Work
- **WHEN** passive evidence establishes already-current state while the agent is active
- **THEN** manual refresh can return a no-op without requiring a mutating maintenance boundary

### Requirement: Failure Reporting Separates Freshness From Native Settlement

Native failures SHALL retain safe partial/unknown effects without rollback, automatic retry, or file restoration claims. Admission SHALL remain closed while operation settlement or native readiness is uncertain; unknown freshness alone SHALL NOT indefinitely block a settled valid runtime. Health, status, interruption, and explicit relaunch SHALL remain responsive.

#### Scenario: Replacement Stops Old Plugin Before Failing
- **WHEN** a native operation stops a plugin and fails to activate its replacement
- **THEN** the result preserves partial effects and the resulting common state
- **AND** it does not claim that the old plugin was restored

#### Scenario: Native Confirmation Is Lost
- **WHEN** response loss or timeout prevents confirmation of a native operation still in progress
- **THEN** outcome remains unknown and native admission remains authoritative until settlement
- **AND** no retry or replacement execution is started

#### Scenario: Only Freshness Evidence Is Missing
- **WHEN** native work is settled and readiness is valid but a resource's freshness remains unverifiable
- **THEN** the result reports unknown freshness without claiming successful verification
- **AND** missing freshness evidence alone does not leave ordinary admission blocked indefinitely

#### Scenario: Operator Inspects an Unsettled Reload
- **WHEN** a native operation leaves readiness uncertain
- **THEN** status and explicit recovery remain responsive while unsafe ordinary work remains blocked

### Requirement: Native Home and Common State Use Typed Bounded Interfaces

The gateway SHALL expose typed `GET /v1/native-home`, `GET /v1/control/refresh` common observation/capabilities, and `POST /v1/control/refresh`. POST SHALL accept only schema version and an optional finite bounded timeout. Results SHALL preserve common state, boundary, identity, native outcome/effects, and safe evidence without private content.

#### Scenario: Caller Reads Common State
- **WHEN** a bound gateway returns a completed common observation with pending or unknown freshness
- **THEN** GET returns HTTP 200 with that typed state and limitations
- **AND** pending freshness is not confused with connection failure

#### Scenario: Invalid Input Is Supplied
- **WHEN** POST contains an invalid timeout, owner/home override, restart flag, replacement content, or unknown field
- **THEN** HTTP 422 is returned before native effects

#### Scenario: Action Outcome Has a Structured Status
- **WHEN** the gateway completes a refresh decision
- **THEN** HTTP 200 covers already-current, confirmed common refresh, or qualified automatic discovery; HTTP 409 preserves busy or common restart-required; and HTTP 501 preserves unsupported control
- **AND** HTTP 503 preserves unavailable, failed, partial/unverified, or uncertain execution with its resource results

### Requirement: Refresh Routing Preserves Managed Authority

An attached gateway SHALL own managed reload admission. Qualified local home and common-state inspection SHALL remain available without starting a gateway. Without a gateway, refresh SHALL permit only qualified no-op/automatic decisions or explicit refusals. Mutating reload SHALL require explicit gateway attachment; no path SHALL attach, launch, or recover execution implicitly.

#### Scenario: Home and State Are Inspected Without a Gateway
- **WHEN** active local authority establishes the native home but no live gateway is attached
- **THEN** local inspection reports the home and qualified common evidence or explicit unknown state without starting a gateway

#### Scenario: Native Reload Has No Gateway
- **WHEN** the selected strategy requires mutation but no live gateway exists
- **THEN** refresh reports the missing authority without pasting a command through another route

#### Scenario: Attached Gateway Refuses Refresh
- **WHEN** an attached owning gateway refuses the managed request
- **THEN** the caller preserves that refusal without falling back to direct body control or relaunch

### Requirement: Common Control Retains Target and Privacy Boundaries

Home/common inspection and refresh SHALL bind to one active locally managed agent. Managed actions SHALL NOT mutate another managed agent's home, shared package installation, or unrelated execution. Missing, ambiguous, stopped, replaced, retired adopted, or external communication-only targets SHALL fail without adoption or recovery. Diagnostics SHALL exclude private material.

#### Scenario: Two Managed Agents Have Distinct Homes
- **WHEN** one of two managed agents in the same project is refreshed after external edits
- **THEN** its broad native operation remains within its owned execution scope
- **AND** the other managed agent's home, process, conversation, and resources remain unchanged

#### Scenario: Target Disappears
- **WHEN** the captured runtime stops or is replaced before native handoff
- **THEN** the request fails or reports uncertainty for that identity without reviving or retargeting execution

#### Scenario: Native Failure Contains Secrets
- **WHEN** a native error contains raw configuration, provider exceptions, or credentials
- **THEN** common results retain only safe reasons and effect evidence
- **AND** no private skill body, configuration document, credential value, or credential-derived fingerprint is published

#### Scenario: Retired Adoption Cannot Supply Home Authority
- **WHEN** a home inspection or refresh selects a retired adopted runtime with a saved native home
- **THEN** Houmao refuses the retired target without inspecting the home or initiating native refresh
- **AND THEN** the provider process and home contents remain intact
