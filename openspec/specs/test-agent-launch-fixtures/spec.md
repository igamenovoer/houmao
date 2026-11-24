# test-agent-launch-fixtures Specification

## Purpose

Define reproducible test-agent launches from generic API cases and locally discovered credentials, with explicit client protocols, isolated private state, and verifiable qualification evidence.

## Requirements

### Requirement: Test launch fixtures expose two generic endpoint cases

The repository SHALL provide secret-free `self-hosted` and `cloud-api` launch descriptors. Case identity SHALL remain independent of client, execution mode, model ID, and credential filename. Maintained defaults SHALL NOT select Qwen3.8, H20 infrastructure, or a personal account.

#### Scenario: Developer selects a self-hosted model
- **WHEN** a developer supplies the self-hosted case with an explicit model and the endpoint required by the selected client
- **THEN** preparation resolves those inputs without requiring a Qwen model name or fixed local port

#### Scenario: Cloud service is configured without creating another case
- **WHEN** a developer selects the cloud API case configured for DeepSeek
- **THEN** the case remains `cloud-api` and its service configuration supplies endpoint and credential references

### Requirement: Client protocols are selected explicitly

Fixture preparation SHALL use Anthropic Messages for Claude, OpenAI Responses for Codex, and OpenAI Chat Completions for the initial Kimi API configuration. DSH SHALL explicitly select its model adapter and protocol: the native DeepSeek route uses Messages, while a generic self-hosted route uses a configured compatible adapter. Endpoint base paths SHALL follow that client's declared convention; support for one protocol SHALL NOT imply another.

#### Scenario: Chat-only server cannot satisfy Codex preparation
- **WHEN** a self-hosted endpoint offers Chat Completions but the selected Codex launch requires Responses
- **THEN** the helper reports the unsupported combination rather than silently switching protocols or inserting a proxy

#### Scenario: DeepSeek endpoints map to the selected client
- **WHEN** the cloud case resolves the existing Anthropic and OpenAI DeepSeek endpoint references
- **THEN** Claude uses the Anthropic endpoint and Codex/Kimi use the corresponding explicitly selected OpenAI protocol
- **AND THEN** an already configured version prefix is not blindly appended or removed

#### Scenario: DSH Uses Its Selected Adapter Protocol
- **WHEN** a DSH fixture selects the native DeepSeek adapter or a generic compatible self-hosted adapter
- **THEN** preparation selects the corresponding Messages or configured compatible protocol and endpoint reference
- **AND THEN** it does not route a Chat-only endpoint into the native Messages transport

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

Every supported fixture run mode SHALL request unattended posture by default. Client-specific invocation SHALL use qualified flags and bootstrap configuration for the installed version. The helper SHALL preserve the distinction between the chosen entrypoint, its supported native controls, and the independent operator prompt policy.

#### Scenario: Kimi prompt mode is selected
- **WHEN** a Kimi headless launch uses its noninteractive prompt mode
- **THEN** the command does not add a TUI-only unattended flag that conflicts with that mode

#### Scenario: TUI preparation encounters an unsupported startup prompt
- **WHEN** the installed client cannot satisfy the selected unattended launch contract
- **THEN** qualification reports that limitation rather than recording an interactive stall as a passing run

### Requirement: Automated fixture tests use synthetic credentials

Unit and integration coverage SHALL exercise both cases, the qualified tool/mode matrix, credential discovery/import, and mode-specific preparation with synthetic credentials and controlled endpoints/processes. Default automated tests SHALL NOT require the developer's env file, saved vendor login, or cloud access.

#### Scenario: CI runs without local accounts
- **WHEN** automated fixture tests execute on a machine without live credentials
- **THEN** the hermetic suite validates resolution and lifecycle wiring without reading personal auth state or issuing paid requests

### Requirement: DSH Headless Fixtures Reuse Generic Local Configuration

The fixture helper SHALL prepare raw and managed one-shot DSH headless CLI launches for `self-hosted` and `cloud-api` using resolved `tool_params`, explicit model and compatibility metadata, and private isolated homes. Cloud preparation SHALL use local key and endpoint references without auth JSON. Explicit endpoint-only `pi-ai/openai-completions` fixtures SHALL use the native authorization placeholder.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Unsupported DSH modes and native login SHALL fail explicitly before authenticated run state is created.

#### Scenario: Fresh Host Uses DeepSeek Without a Local Model
- **WHEN** a developer provides the cloud key, the selected Messages-compatible endpoint, and an explicit model through the local fixture configuration
- **THEN** a native DSH headless test agent can be prepared without a deployed self-hosted model or saved vendor-login files

#### Scenario: Generic Self-Hosted Route Has No Explicit Capabilities
- **WHEN** a self-hosted DSH route lacks model capacity or `reasoning_efforts` metadata required by its selected adapter
- **THEN** preparation fails with those missing inputs named instead of borrowing another model's defaults

#### Scenario: CI Has No Local Provider Account
- **WHEN** hermetic DSH fixture tests execute without local credentials
- **THEN** synthetic endpoints and subprocesses validate preparation and lifecycle without paid requests or personal auth discovery

#### Scenario: Self-Hosted Fixture Can Complete an Endpoint-Only Prompt
- **WHEN** a developer prepares a self-hosted `pi-ai/openai-completions` fixture with explicit `reasoning_efforts`, `compat` overrides, and an endpoint that accepts the placeholder authorization header
- **THEN** fixture preparation emits `tool_params` with `api_key_env: null`, the configured `compat` mapping, and `reasoning_efforts`
- **AND THEN** the launched fixture completes a prompt with the native placeholder and without an operator-supplied API key

#### Scenario: Managed and raw fixtures select the same native profile

- **WHEN** a developer qualifies the raw and managed headless fixtures with matching inputs
- **THEN** both exercise `--profile headless --json` and exact native continuation through a new worker per prompt

### Requirement: DSH Web Fixtures Share the Existing Generic Endpoint Cases

DSH `web` fixture preparation SHALL reuse the `self-hosted` and `cloud-api` cases, `DshToolParams` compatibility and reasoning inputs, and private credential/run roots established for headless DSH. Raw and managed preparation SHALL expose the same native Web behavior. Browser startup and connection credentials SHALL remain controlled locally without entering tracked reports.

#### Scenario: A Fresh Host Uses Cloud DSH Interactively
- **WHEN** a developer configures only the selected DeepSeek key, endpoint, and model
- **THEN** a DSH Web test agent can be prepared without a self-hosted model, auth JSON, or desktop display

#### Scenario: A Browser Connects to the Managed Fixture
- **WHEN** a qualification browser signs in through the fixture's private local connection mechanism
- **THEN** it opens the same native session targeted by the programmatic adapter
- **AND THEN** public fixture summaries contain only non-secret location and identity metadata

#### Scenario: Self-Hosted Web Fixture Shares Tool-Params Compatibility Inputs
- **WHEN** a developer prepares a `mode=web` self-hosted `pi-ai/openai-completions` DSH fixture with explicit `compat` and `reasoning_efforts` settings
- **THEN** raw and managed Web preparations emit the same DSH `tool_params` compatibility, reasoning, and endpoint-only contract as headless DSH

### Requirement: DSH Web Qualification Exercises Mixed Control and Admission Races

Qualification SHALL exercise actual browser and API clients on the same native session, including human/program prompts, progress, human questions, interruption, readiness races, restart, and usage. Deterministic coverage SHALL use controlled models/processes and synthetic credentials. Live provider qualification SHALL record actual evidence separately.

#### Scenario: Browser and Program Both Drive the Session
- **WHEN** a browser submits work, the API observes it, and a later API prompt is submitted
- **THEN** both clients observe one native history with correct terminal outcomes

#### Scenario: Browser Input Races Ordinary Programmatic Delivery
- **WHEN** a controlled test starts human work after API readiness inspection but before native admission
- **THEN** the ordinary API attempt is refused and never appears in the native inbox after the human turn ends

#### Scenario: Restart Follows Uncertain Admission
- **WHEN** the qualification host dies or loses its response after native admission
- **THEN** the attempt reports failure or uncertainty and explicit recovery does not replay its input

#### Scenario: No Real Account Exists in CI
- **WHEN** hermetic Web qualification runs without developer credentials
- **THEN** browser/API coexistence and lifecycle behavior are tested using controlled endpoints without paid provider calls

### Requirement: Fixture qualification records build and evidence for each native run mode

Qualification SHALL record build, model, protocol, case, run mode, backend, native surface, and outcome without credentials. Live tests for the run-mode changes SHALL use the explicitly selected self-hosted Qwen 3.8 model and record missing prerequisites per client and mode. The fixture SHALL retain its supported DeepSeek configuration and validate that path with synthetic credentials in automated tests.

#### Scenario: Self-hosted endpoint is not configured
- **WHEN** live qualification has no configured compatible self-hosted endpoint/model
- **THEN** its report marks those live lanes as not run with the missing prerequisite
- **AND THEN** passing hermetic tests do not become a live qualification claim

#### Scenario: Historical capture records Qwen usage
- **WHEN** an existing sanitized accounting fixture records an earlier Qwen capture
- **THEN** it retains its factual model/version metadata
- **AND THEN** maintained launch helpers do not depend on the historical change-local wrapper

#### Scenario: DSH Service Evidence Identifies Its Mode
- **WHEN** a DSH ACP service smoke passes against the selected endpoint
- **THEN** its report records service with the qualified ACP backend
- **AND THEN** Claude, Codex, and Kimi retain their required headless and unattended TUI lanes

#### Scenario: DSH Web Qualification Uses the Native Browser Surface
- **WHEN** a DSH fixture selects `mode=web`
- **THEN** qualification launches its Web Host and records Web API and browser evidence
- **AND THEN** a tmux log capture or passing ACP run does not qualify the interactive lane

### Requirement: DSH Web qualification verifies managed Workspace navigation

Qualification SHALL use the maintained managed DSH Web fixture to verify native Workspace membership and browser selection for the published session. It SHALL collect evidence before the first prompt and observe browser entry and reload without test-only Workspace setup or session selection.

#### Scenario: A clean browser opens a fresh managed session

- **WHEN** a clean browser follows the gateway Web entry flow before any prompt
- **THEN** the native Workspace for the configured working directory lists the bound session and the browser selects it
- **AND THEN** the Workspace and session inventories are identical before entry, after entry, and after reload

#### Scenario: Explicit relaunch preserves or replaces the expected session

- **WHEN** qualification enters through the gateway after exact relaunch of a session with history and after an explicit new-session relaunch
- **THEN** exact relaunch opens the same session with its history and new-session relaunch opens one replacement in the same Workspace
- **AND THEN** previously existing sessions and unrelated Workspace records are preserved

#### Scenario: A notifier turn follows the manifest binding

- **WHEN** an operator selects an unrelated native session and the gateway mail notifier dispatches a turn
- **THEN** the fixture observes that turn in the manifest-bound native conversation after reopening the managed entry
- **AND THEN** the unrelated conversation and the managed binding retain their original identities

### Requirement: Kimi fixtures share a native model catalog across launch surfaces

Both Kimi API fixture cases SHALL write a private native `config.toml` from their selected provider, endpoint, alias, and model metadata. Raw and managed launches SHALL use the same configuration inputs. Fixture models that offer multiple thinking levels SHALL declare ordered native labels in `support_efforts`. Config-owned values SHALL be absent from launch env.

#### Scenario: Kimi API fixtures run the same config-backed model directly and through Houmao

- **WHEN** a developer prepares the same Kimi API case with an explicitly selected endpoint, model, and metadata for raw and managed launch
- **THEN** both private homes use the same provider type, endpoint, model ID, alias, and capabilities in native config
- **AND THEN** the fixture uses the selected credential without requiring OAuth token storage or an env-model selector

#### Scenario: A private fixture config is sufficient for managed numeric reasoning

- **WHEN** an explicitly selected Kimi model exposes multiple efforts and its fixture credential config declares the ordered labels
- **AND WHEN** the managed Web launch selects that alias and a numeric reasoning level through the project profile
- **THEN** launch succeeds with the native label at the selected position and Kimi exposes its configured effort options
- **AND THEN** the setup bundle needs no duplicate catalog and neither the owning tmux session nor an ordinary pane has config-owned Kimi env bindings

### Requirement: Managed fixtures qualify communication across isolated tmux servers

Automated coverage SHALL use `--tmux-server new` to exercise two managed fixture runs on separate owned tmux sockets with shared registry and mail authority. It SHALL verify record-backed peer discovery and mail under the fixture’s socket restrictions, plus authorized direct prompt delivery with gateways detached. The tests SHALL use synthetic inputs and affect only their isolated servers and owned sessions.

#### Scenario: Peer lookup and mail work while peer tmux access is blocked

- **WHEN** two prepared managed agents share a registry and offline mail authority and neither has an attached gateway
- **AND WHEN** the sender's command environment refuses access to the recipient's socket
- **THEN** the sender resolves the registered recipient's mailbox through the normal CLI without a peer tmux invocation
- **AND THEN** sending through the sender's own mailbox commits a message that the recipient can retrieve

#### Scenario: A reachable gateway is reported through its own evidence

- **WHEN** the recipient publishes a verified live gateway and its terminal is inaccessible to the sender
- **THEN** record-backed discovery can return the recipient's live gateway binding without probing the recipient's tmux server

#### Scenario: Authorized direct prompt uses the recorded recipient

- **WHEN** both gateways are detached and the test provides an authorized route to the selected TUI peer's socket
- **THEN** a normal managed prompt hands off input to the peer's recorded pane
- **AND THEN** the sender's session and unrelated terminal sessions receive no input

### Requirement: Local tmux-backed fixtures default to the Houmao server

Managed fixture launches and fixture-owned raw TUI or Web launches SHALL select `houmao-default` unless preparation explicitly selects `--tmux-server new`. Managed fixtures SHALL express the choice in their launch profile. Raw headless launches SHALL remain process-only. Passive launches SHALL use the addressed server’s own socket policy.

#### Scenario: Managed fixtures share the default server

- **WHEN** two local managed fixtures with separate initially empty registries launch without a tmux override in the same owner scope
- **THEN** each uses a profile selecting `houmao-default`
- **AND THEN** their run metadata records distinct owned sessions on the same concrete socket

#### Scenario: A raw tmux-backed fixture uses the default server

- **WHEN** a raw terminal or Web fixture launches without a tmux override
- **THEN** its owned session starts on the owner’s Houmao default socket
- **AND THEN** the fixture keeps selected provider credentials out of shared tmux state

#### Scenario: An isolated fixture explicitly requests a new server

- **WHEN** an operator prepares and launches two local tmux-backed fixtures using `--tmux-server new`
- **THEN** each run uses its own socket and retains that socket for follow-up actions

### Requirement: Fixture lifecycle uses captured ownership on either server

Fixture follow-up and cleanup SHALL use the captured agent or verify the run’s ownership at its captured terminal coordinates. Tmux-backed fixture tests SHALL use isolated test-owned socket resources, including tests of the shared default.

#### Scenario: One shared fixture stops without affecting another

- **WHEN** two fixture runs have active sessions on the same test-owned Houmao default server
- **AND WHEN** the operator stops the first run
- **THEN** only that run’s session stops and the second run can still be controlled

#### Scenario: A fixture follow-up runs from another tmux server

- **WHEN** the caller’s enclosing tmux socket differs from the run’s saved socket
- **THEN** fixture checks and terminal operations use the saved binding for that run
