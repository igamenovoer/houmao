# Spec Delta

## Purpose

Define reproducible test-agent launches from generic API cases and locally discovered credentials, with explicit client protocols, isolated private state, and verifiable qualification evidence.

## ADDED Requirements

### Requirement: Test launch fixtures expose two generic endpoint cases

The repository SHALL provide secret-free `self-hosted` and `cloud-api` launch descriptors. Case identity SHALL remain independent of client, execution mode, model ID, and credential filename. Maintained defaults SHALL NOT select Qwen3.8, H20 infrastructure, or a personal account.

#### Scenario: Developer selects a self-hosted model
- **WHEN** a developer supplies the self-hosted case with an explicit model and the endpoint required by the selected client
- **THEN** preparation resolves those inputs without requiring a Qwen model name or fixed local port

#### Scenario: Cloud service is configured without creating another case
- **WHEN** a developer selects the cloud API case configured for DeepSeek
- **THEN** the case remains `cloud-api` and its service configuration supplies endpoint and credential references

### Requirement: Client protocols are selected explicitly

Fixture preparation SHALL use Anthropic Messages for Claude, OpenAI Responses for Codex, and OpenAI Chat Completions for the initial Kimi API configuration. Support for one protocol SHALL NOT establish support for another. Endpoint base paths SHALL follow the selected protocol's declared convention.

#### Scenario: Chat-only server cannot satisfy Codex preparation
- **WHEN** a self-hosted endpoint offers Chat Completions but the selected Codex launch requires Responses
- **THEN** the helper reports the unsupported combination rather than silently switching protocols or inserting a proxy

#### Scenario: DeepSeek endpoints map to the selected client
- **WHEN** the cloud case resolves the existing Anthropic and OpenAI DeepSeek endpoint references
- **THEN** Claude uses the Anthropic endpoint and Codex/Kimi use the corresponding explicitly selected OpenAI protocol
- **AND THEN** an already configured version prefix is not blindly appended or removed

### Requirement: Models and capabilities are explicit launch inputs

API preparation SHALL require a selected model and SHALL validate client-required model metadata. Reasoning effort, context size, reasoning-field mapping, and image support SHALL come from explicit configuration or qualified model metadata. The helper SHALL NOT copy capabilities from an unrelated model or invent missing required metadata.

#### Scenario: Model selection is missing
- **WHEN** no model is supplied by the selected configuration or invocation
- **THEN** preparation fails with the missing input named before creating an agent

#### Scenario: Kimi needs context metadata
- **WHEN** the selected Kimi configuration lacks context metadata required to represent its model correctly
- **THEN** the helper requests that configuration through an actionable error instead of assuming the old Qwen context window

### Requirement: Cloud credentials resolve through local references

The initial cloud configuration SHALL reference `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL_ANTHROPIC`, and `DEEPSEEK_BASE_URL_OPENAI`. Explicit process values SHALL take precedence over an explicitly selected local env file. Env files SHALL be parsed as data without shell execution. Real key values SHALL NOT appear in tracked assets, command traces, or shareable reports.

#### Scenario: Local env file supplies the cloud key
- **WHEN** the operator selects a local env file containing the configured DeepSeek variables
- **THEN** the helper maps the key into only the selected client's credential channel
- **AND THEN** tracked configuration and displayed commands retain references rather than the key value

#### Scenario: Cloud key is absent
- **WHEN** the cloud case has no non-empty configured API key
- **THEN** preparation fails explicitly and does not substitute an anonymous placeholder or native login credentials

#### Scenario: Env file contains shell syntax
- **WHEN** a selected env file contains command substitution or shell statements
- **THEN** the helper does not execute them
- **AND THEN** unsupported syntax produces a safe configuration error

### Requirement: Auth discovery is bounded and read-only

The helper SHALL discover supported credential files only for the selected tool, using its configured home, standard home, or explicitly supplied search roots. It SHALL report candidate IDs, paths, kinds, and importability without secret contents. Discovery SHALL NOT modify source files, execute credential helpers, or traverse outside the selected search boundaries.

#### Scenario: Codex home contains cached login state
- **WHEN** the selected Codex home contains a supported `auth.json`
- **THEN** discovery reports an importable candidate without printing tokens or changing the file

#### Scenario: Claude and Kimi credentials are discoverable
- **WHEN** a selected Claude home contains `.credentials.json` or a selected Kimi home contains `credentials/kimi-code.json`
- **THEN** discovery identifies the tool-specific candidate and supported companion files separately from history and sessions

#### Scenario: Additional root contains an escaping symlink
- **WHEN** a search-root entry resolves outside its allowed root
- **THEN** discovery excludes that entry and does not widen its scan

#### Scenario: Active credentials are not file-importable
- **WHEN** only a keychain-backed or helper-only auth method is found
- **THEN** discovery reports the limitation without exporting credentials or inventing a JSON auth file

### Requirement: Auth import copies a selected candidate into private local storage

Import SHALL require an explicit candidate or source selection and SHALL copy only supported files into the external local credential store. Opaque login JSON SHALL retain its original contents. Source credentials SHALL remain unchanged. Duplicate targets SHALL fail unless replacement is explicit; imported files SHALL have user-only access.

#### Scenario: Several credentials are discovered
- **WHEN** discovery finds multiple valid candidates and import has no explicit selection
- **THEN** import reports the candidates and creates no credential bundle

#### Scenario: Selected vendor state is imported
- **WHEN** an operator imports one supported candidate
- **THEN** the local store receives only its supported auth and companion files
- **AND THEN** the source bytes and metadata are not rewritten by the import

#### Scenario: Existing bundle is protected from accidental replacement
- **WHEN** import targets an existing local bundle without an explicit replace option
- **THEN** import fails without changing the existing bundle

### Requirement: Credential-bearing fixture state stays outside the checkout

Reusable live auth SHALL default to an XDG data directory and private run state SHALL default to an XDG state directory, with explicit root overrides. Resolved credential and private run roots SHALL be outside the repository checkout. Tracked fixtures SHALL contain no live auth JSON, and runtime projections SHALL not write credentials into tracked fixture trees.

#### Scenario: Developer overrides a root into the checkout
- **WHEN** a credential or private run root resolves inside the checkout, including through a symlink
- **THEN** preparation/import fails before writing credential material there

#### Scenario: Fresh checkout has no saved auth files
- **WHEN** a developer inspects tracked fixture assets before local setup
- **THEN** descriptors, seed assets, and discovery instructions suffice to explain preparation without requiring a saved real auth file

### Requirement: Native login state remains independent of API case selection

API-key cases SHALL NOT require native auth JSON. Vendor-login tests SHALL select imported native state explicitly and preserve its provider-owned routing rather than attaching it implicitly to DeepSeek or a self-hosted API case. Auth discovery/import SHALL remain usable without launching an agent.

#### Scenario: DeepSeek launch has no auth JSON
- **WHEN** valid cloud API credentials and endpoint/model settings exist without any imported native login bundle
- **THEN** the API launch can be prepared for each supported client

#### Scenario: Vendor-login smoke selects imported state
- **WHEN** a vendor-login smoke explicitly selects a local imported bundle
- **THEN** preparation uses that native auth method without reclassifying it as a third generic API endpoint case
- **AND THEN** the helper does not inject DeepSeek routing into the vendor-login run

### Requirement: Preparation creates isolated client homes from current seed assets

Each preparation SHALL create fresh private run state and a new client home without inherited history or sessions. It SHALL project only selected credentials, setup, prompts, and skills. Competing ambient provider authentication and routing SHALL be excluded so the selected test configuration determines the backend.

#### Scenario: Developer prepares the same lane twice
- **WHEN** two runs use the same case, client, and execution mode
- **THEN** their run identities and homes differ and neither copies the other's native history

#### Scenario: Parent shell contains another provider account
- **WHEN** the selected API configuration differs from ambient credentials or routing
- **THEN** the launched client receives only the selected credential/routing settings and does not silently use that other account

### Requirement: Raw and managed launches share resolved fixture configuration

Raw client qualification and managed test-agent creation SHALL consume the same resolved model, protocol, endpoint, auth selection, and model metadata. Managed creation SHALL use a fresh project overlay and maintained project credential/specialist/launch behavior. Existing runtime services SHALL remain responsible for managed lifecycle and accounting.

#### Scenario: Managed qualification follows raw qualification
- **WHEN** one resolved cloud configuration is used for a raw capture and a managed agent run
- **THEN** both launches use equivalent backend inputs while retaining separate homes and run identities

#### Scenario: Managed launch returns an authoritative identity
- **WHEN** the helper launches a project-backed test agent
- **THEN** it returns the resulting managed agent and session identity for supported follow-up operations
- **AND THEN** it does not implement a parallel gateway or accounting recorder

### Requirement: Automated test launches default to unattended posture

Headless and TUI fixture launches SHALL request unattended posture by default. Client-specific invocation SHALL use qualified flags and bootstrap configuration for the installed version. The helper SHALL preserve the distinction between headless prompt mode and TUI permission flags.

#### Scenario: Kimi prompt mode is selected
- **WHEN** a Kimi headless launch uses its noninteractive prompt mode
- **THEN** the command does not add a TUI-only unattended flag that conflicts with that mode

#### Scenario: TUI preparation encounters an unsupported startup prompt
- **WHEN** the installed client cannot satisfy the selected unattended launch contract
- **THEN** qualification reports that limitation rather than recording an interactive stall as a passing run

### Requirement: Fixture qualification records actual evidence and limitations

Qualification SHALL record the actual client version, model, protocol, case, execution surface, and outcome without credentials. DeepSeek SHALL be exercised in headless and unattended TUI modes for all three clients. Self-hosted live qualification SHALL use an explicitly configured model other than Qwen3.8 when available; unavailable prerequisites SHALL be reported without a success claim.

#### Scenario: Self-hosted endpoint is not configured
- **WHEN** live qualification has no configured compatible self-hosted endpoint/model
- **THEN** its report marks those live lanes as not run with the missing prerequisite
- **AND THEN** passing hermetic tests do not become a live qualification claim

#### Scenario: Historical capture records Qwen usage
- **WHEN** an existing sanitized accounting fixture records an earlier Qwen capture
- **THEN** it retains its factual model/version metadata
- **AND THEN** maintained launch helpers do not depend on the historical change-local wrapper

### Requirement: Automated fixture tests use synthetic credentials

Unit and integration coverage SHALL exercise both cases, all three clients, credential discovery/import, and headless/TUI preparation with synthetic credentials and controlled endpoints/processes. Default automated tests SHALL NOT require the developer's env file, saved vendor login, or cloud access.

#### Scenario: CI runs without local accounts
- **WHEN** automated fixture tests execute on a machine without live credentials
- **THEN** the hermetic suite validates resolution and lifecycle wiring without reading personal auth state or issuing paid requests
