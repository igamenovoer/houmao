# Spec Delta

## MODIFIED Requirements

### Requirement: Client protocols are selected explicitly

Fixture preparation SHALL use Anthropic Messages for Claude, OpenAI Responses for Codex, and OpenAI Chat Completions for the initial Kimi and Hermes API configuration. DSH SHALL explicitly select its model adapter and protocol: the native DeepSeek route uses Messages, while a generic self-hosted route uses a configured compatible adapter. Endpoint base paths SHALL follow that client's declared convention; support for one protocol SHALL NOT imply another.

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

#### Scenario: Hermes Uses the Selected Chat Completions Route

- **WHEN** a Hermes fixture selects a model and compatible endpoint under a generic case
- **THEN** preparation configures that Chat Completions route in the private Hermes home
- **AND THEN** it does not infer an endpoint, model, or credential from personal Hermes state

## ADDED Requirements

### Requirement: Hermes Fixtures Qualify Each Supported Run Mode

The fixture workflow SHALL support separate raw and managed Hermes qualification for tui, service, and headless. A run SHALL record the selected model and route, executable build, qualified capabilities, and per-mode evidence without secrets.

#### Scenario: Hermes Qualification Exercises an Isolated Local Runtime

- **WHEN** a developer selects a supported Hermes mode and a controlled self-hosted test configuration
- **THEN** raw and managed lanes use independently isolated homes and exact workspace and model inputs
- **AND THEN** the TUI lane uses an isolated tmux server
- **AND THEN** an unavailable fixture or provider route is recorded separately from a passing qualification
