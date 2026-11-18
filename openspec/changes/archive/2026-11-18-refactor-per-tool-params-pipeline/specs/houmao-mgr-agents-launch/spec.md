# houmao-mgr-agents-launch Specification

## ADDED Requirements

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
