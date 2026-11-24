# houmao-mgr-agents-launch Specification

## Purpose
Define retained managed-agent birth contracts for project-backed launch and internal native construction without requiring `houmao-server`.
## Requirements
### Requirement: Managed launch establishes primary tmux surface independent of user base indexes
Retained managed-agent birth surfaces such as `houmao-mgr project agents launch` SHALL start Houmao-owned tmux-backed managed-agent sessions successfully when the user's tmux configuration sets non-zero default window or pane base indexes, provided tmux otherwise supports creating and moving the session's bootstrap surface.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

For launched tmux-backed sessions, the command SHALL publish managed-agent metadata only after the runtime has established the contractual primary window index `0` and captured the primary tmux object handles needed for later operations.

If the primary surface cannot be established, launch SHALL fail before publishing an active shared-registry record for the attempted managed agent.

#### Scenario: Launch succeeds with one-based tmux indexes
- **WHEN** an operator's tmux configuration sets `base-index 1` and `pane-base-index 1`
- **AND WHEN** the operator runs `houmao-mgr project agents launch` for a local tmux-backed provider
- **THEN** the launched managed-agent session owns primary window index `0`
- **AND THEN** the manifest records primary tmux object handles for the managed-agent surface
- **AND THEN** later prompt, capture, interrupt, gateway, and relaunch operations can target that primary surface without relying on `session:0.0`

#### Scenario: Failed primary-surface preparation does not publish active launch metadata
- **WHEN** a retained managed-agent birth command creates a tmux session but cannot establish the managed-agent primary window at index `0`
- **THEN** the command reports launch failure
- **AND THEN** it does not publish an active lifecycle-aware managed-agent registry record for that failed launch

### Requirement: Managed-agent birth is source-scoped rather than global management
The maintained global managed-agent management surface SHALL NOT expose a first-birth launch command.

Project-backed managed-agent birth SHALL be represented by:

```text
houmao-mgr project [--project-dir <dir>] agents launch
```

Direct native/provider construction plumbing, when retained, SHALL live under internal native-agent command surfaces rather than `houmao-mgr agents global`.

Existing local managed-agent identities MAY be adopted into the registry through `houmao-mgr agents self join` when the target is the caller's current tmux session.

#### Scenario: Global management omits launch
- **WHEN** an operator runs `houmao-mgr agents global --help`
- **THEN** the help output does not list `launch`
- **AND THEN** the operator must choose a source-scoped birth command or a join/import command instead

#### Scenario: Project launch remains public birth path
- **WHEN** an operator wants to create a managed agent from project profile `reviewer`
- **THEN** the maintained command path is `houmao-mgr project agents launch --profile reviewer`
- **AND THEN** the launch resolves source definitions from the selected project overlay rather than from global registry state

### Requirement: Project agent launch validates only the selected birth source
`houmao-mgr project agents launch` SHALL resolve and validate only the operator-selected birth source and the definitions needed to launch that source.

The command SHALL NOT parse every project preset, profile, or launch profile in a way that can make stale unrelated records block the selected launch.

The command SHALL still fail before publishing active managed-agent registry metadata when the selected source or its dependencies contain invalid launch configuration.

#### Scenario: Specialist launch ignores unrelated stale preset
- **WHEN** an unrelated project preset contains removed system-skill selector `houmao-agent-ag-ui`
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist test-claude-kimi --name startup-graphics-test`
- **THEN** the command does not fail because of the unrelated preset
- **AND THEN** any launch failure is tied to `test-claude-kimi`, its selected source dependencies, tmux setup, credentials, gateway setup, or provider startup

#### Scenario: Selected invalid specialist fails before registry publish
- **WHEN** the selected specialist or selected launch source contains removed system-skill selector `houmao-agent-ag-ui`
- **AND WHEN** an operator runs `houmao-mgr project agents launch` for that source
- **THEN** the command fails before publishing active managed-agent registry metadata
- **AND THEN** the error identifies the selected source and the removed selector

### Requirement: Project launch supports explicit execution-profile selection

`houmao-mgr project agents launch` SHALL accept `--executor <name>` to select a trusted named execution profile independently of `--profile` or `--specialist`. Omitting `--executor` SHALL retain current-account launch. Project source selection SHALL occur in the target project; execution selection SHALL NOT create a global first-birth surface or allow project definitions to supply delegation authority.

#### Scenario: Launch profile and execution profile select different concerns

- **WHEN** an operator launches with `--profile reviewer --executor worker-alice`
- **THEN** `worker-alice` determines the admitted execution context
- **AND THEN** `reviewer` resolves the selected birth source and launch defaults within that context's project

#### Scenario: Omitted executor preserves current-account birth

- **WHEN** an operator runs a supported project launch without `--executor`
- **THEN** the launch executes under the current account and records its observed execution binding
- **AND THEN** it does not infer another account from a profile name, agent name, or private-key reference

### Requirement: Delegated launch validates target inputs before preparing runtime state

Delegated launch SHALL hand off before project bootstrap, catalog projection, credential materialization, home creation, or tmux creation. Supplied target project and workdir paths SHALL be validated in the owner context. Missing or unsupported selected inputs SHALL fail before active owner publication or successful operator-locator publication. Launch preparation SHALL retain selected-source-scoped validation.

#### Scenario: Remote-only project and workdir pass owner-side validation

- **WHEN** the selected execution profile identifies an accessible target project and the requested workdir exists there but not on the operator's host
- **THEN** caller-side path validation does not reject the launch
- **AND THEN** the owner resolves selected definitions and creates runtime artifacts in the target context

#### Scenario: Invalid selected target source has no caller-local fallback

- **WHEN** the selected target project lacks the requested profile or its required credential reference
- **THEN** launch reports that target-side configuration failure
- **AND THEN** it does not prepare a caller-local agent or publish a successful execution locator

#### Scenario: Unrelated invalid target profile does not block launch

- **WHEN** an unselected target profile is stale but the selected target source and dependencies are valid
- **THEN** delegated launch validates the selected source without loading unrelated profiles as launch prerequisites

### Requirement: Project agent launch accepts one-shot per-tool parameter overrides

`houmao-mgr project agents launch` SHALL accept `--tool-params <json-or-@path>` as a one-shot override above stored specialist and launch-profile parameters. The execution owner SHALL resolve referenced files. The stored definitions SHALL retain their reusable values.

#### Scenario: One-shot launch tool_params overrides profile tool_params for one instance
- **WHEN** an operator runs `houmao-mgr project agents launch --profile reviewer --tool-params '{"include_partial_messages":true}'` for a Claude headless profile
- **THEN** the launched instance resolves `include_partial_messages = true` in its brain manifest
- **AND THEN** stored profile `reviewer` remains unchanged in the project catalog

### Requirement: Managed launch validates effective parameters before runtime mutation

The execution owner SHALL merge and validate the effective parameters, selected backend, model, and credential binding before creating runtime state or performing a force takeover. Brain construction and launch planning SHALL use the same configuration accepted by preflight.

#### Scenario: Invalid merged inputs fail before force takeover
- **WHEN** an operator requests a force launch with a valid partial override that becomes invalid after merging or conflicts with the selected backend, model, or credential binding
- **THEN** the execution owner rejects the launch before stopping the predecessor, writing the replacement home, or removing predecessor artifacts
- **AND THEN** the existing agent continues serving with its original runtime state in either force mode

#### Scenario: Build uses the configuration accepted by preflight
- **WHEN** the execution owner validates a managed launch using a file-referenced one-shot override
- **THEN** brain construction and launch planning use the effective parameters and binding selected by preflight, even if an authoring layer changes after validation

### Requirement: Project launch selects the native run mode before takeover

Project birth SHALL accept a single `--mode` selector, resolve the selected source and its defaults in the admitted execution context, and validate the tool, mode, and backend-specific options before force takeover, home creation, or live publication.

#### Scenario: An unsupported override targets a predecessor

- **WHEN** an operator requests DSH tui with force replacement of an existing managed agent
- **THEN** the request identifies the unsupported pair and leaves the predecessor running

#### Scenario: A delegated launch supplies an explicit mode

- **WHEN** an operator launches a profile through a named executor with an explicit supported mode
- **THEN** owner-side resolution applies the mode and returns the same tool/mode/backend binding that it persists

### Requirement: Project birth resolves tmux selection as one launch input

`houmao-mgr project agents launch` SHALL accept `--tmux-server` and `--tmux-socket-path` as a one-shot selector. An explicit selector SHALL replace the stored profile selector for that birth. When both are omitted, the existing execution scope and shell selection SHALL apply. `--session-name` SHALL name the session on the resolved server.

#### Scenario: A one-shot selector overrides the stored choice

- **GIVEN** a launch profile with `server: socket` and an absolute `socket_path`
- **WHEN** a new birth specifies `--tmux-server houmao-default`
- **THEN** the runtime uses the Houmao default server for that birth
- **AND THEN** profile inspection still reports the stored socket selector

#### Scenario: Launch without a selector retains the enclosing server

- **WHEN** a current-account launch has no explicit execution scope and both tmux selectors are omitted inside a tmux session
- **THEN** the launch uses the enclosing server

### Requirement: Project birth validates tmux selection before takeover

The execution owner SHALL validate the effective tmux selector and its startup permission before force takeover or creation of agent runtime state. An admitted executor’s socket binding SHALL constrain the result. An invalid or incompatible selection or an unavailable existing-only server SHALL fail before stopping a predecessor.

#### Scenario: A selector conflicts with the admitted executor

- **WHEN** a delegated project launch requests a tmux socket different from the admitted owner’s bound socket
- **THEN** the owner reports the conflict and leaves both servers and any predecessor untouched

#### Scenario: The requested existing server is unavailable before a force launch

- **WHEN** a force replacement selects `socket` and the execution owner cannot reach that server during preflight
- **THEN** launch fails at the specified socket and the existing agent continues on its original binding

#### Scenario: A replacement would stop the selected existing-only server

- **GIVEN** the force predecessor owns the only session on an existing-only server that exits when empty
- **WHEN** a force replacement selects that same server
- **THEN** the launch either preserves the running server through handoff or rejects the replacement before stopping the predecessor
