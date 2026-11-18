# Houmao Manager Agents Launch Spec Delta

## ADDED Requirements

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

