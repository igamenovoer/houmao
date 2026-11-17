# Spec Delta

## MODIFIED Requirements

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


### Requirement: Fixture qualification records actual evidence and limitations

Qualification SHALL record actual client version/build, model, protocol, case, native surface, and outcome without credentials. DeepSeek SHALL be exercised for every supported client/mode pair; this change adds DSH ACP headless coverage. Self-hosted live qualification SHALL use an explicitly configured model other than Qwen3.8 when available; unavailable prerequisites SHALL be reported without a success claim.

#### Scenario: Self-hosted endpoint is not configured
- **WHEN** live qualification has no configured compatible self-hosted endpoint/model
- **THEN** its report marks those live lanes as not run with the missing prerequisite
- **AND THEN** passing hermetic tests do not become a live qualification claim

#### Scenario: Historical capture records Qwen usage
- **WHEN** an existing sanitized accounting fixture records an earlier Qwen capture
- **THEN** it retains its factual model/version metadata
- **AND THEN** maintained launch helpers do not depend on the historical change-local wrapper

#### Scenario: DSH Headless Qualification Does Not Imply Interactive Support
- **WHEN** a DSH ACP cloud smoke passes
- **THEN** its report records headless ACP as the qualified control surface
- **AND THEN** Claude, Codex, and Kimi retain their required headless and unattended TUI lanes


## ADDED Requirements

### Requirement: DSH Headless Fixtures Reuse Generic Local Configuration

The fixture helper SHALL prepare raw and managed DSH ACP launches from `self-hosted` and `cloud-api` cases with explicit model metadata and isolated private homes. Cloud preparation SHALL use local key and endpoint references without auth JSON. Unimplemented DSH mode or native-login selections SHALL fail explicitly before creating authenticated run state.

#### Scenario: Fresh Host Uses DeepSeek Without a Local Model
- **WHEN** a developer provides the cloud key, the selected Messages-compatible endpoint, and an explicit model through the local fixture configuration
- **THEN** a DSH ACP test agent can be prepared without a deployed self-hosted model or saved vendor-login files

#### Scenario: Generic Self-Hosted Route Has No Explicit Capabilities
- **WHEN** a self-hosted DSH route lacks model capacity or compatibility metadata required by its selected adapter
- **THEN** preparation fails with those missing inputs named instead of borrowing another model's defaults

#### Scenario: CI Has No Local Provider Account
- **WHEN** hermetic DSH fixture tests execute without local credentials
- **THEN** synthetic endpoints and subprocesses validate preparation and lifecycle without paid requests or personal auth discovery
