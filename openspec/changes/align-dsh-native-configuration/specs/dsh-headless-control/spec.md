# dsh-headless-control Specification

## ADDED Requirements

### Requirement: DSH Headless Failures Surface Secret-Redacted Provider Diagnostics

When a managed DSH ACP request returns a JSON-RPC error or an ACP worker fails before completing initialization or prompt settlement, Houmao SHALL include a bounded, secret-redacted diagnostic summary of the remote error message or worker failure output in the surfaced execution error while preserving full raw diagnostics only in user-private turn artifacts. Resolved secret environment values and bearer or API-key tokens SHALL never appear in surfaced error text.

#### Scenario: Upstream HTTP Rejection Surfaces Redacted Detail
- **WHEN** an upstream model endpoint rejects a DSH ACP turn with an HTTP or provider validation message carried inside a JSON-RPC error response
- **THEN** the failed turn reports both the JSON-RPC error code and the sanitized error message across CLI stderr and gateway turn status
- **AND THEN** operators are not left with a bare `ACP request failed (-32603)` string

#### Scenario: Secret Values Are Redacted From Surfaced ACP Errors
- **WHEN** a JSON-RPC error payload or worker stderr output contains a resolved API key value or bearer token from the DSH private environment
- **THEN** Houmao replaces the secret value with `[REDACTED]` before surfacing the diagnostic in exceptions, gateway responses, or console logs

#### Scenario: Worker Startup Crash Surfaces Sanitized Stderr Summary
- **WHEN** the DSH ACP worker exits or closes stdout before answering initialization due to a configuration or plugin error written to stderr
- **THEN** the surfaced protocol failure includes a bounded, secret-redacted summary of the worker stderr output alongside the failure status
