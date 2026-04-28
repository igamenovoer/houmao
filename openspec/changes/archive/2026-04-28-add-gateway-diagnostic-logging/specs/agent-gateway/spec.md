## ADDED Requirements

### Requirement: Gateway supports opt-in rotating diagnostic logs
The gateway SHALL support an opt-in diagnostic logging mode that writes bounded rotating diagnostic log files under the gateway-owned log directory.

Diagnostic logging SHALL be disabled by default when no explicit gateway diagnostic logging configuration is present.

When diagnostic logging is enabled, the gateway SHALL write line-oriented structured diagnostic entries to a dedicated diagnostic log path separate from the human-oriented `gateway.log`.

The diagnostic log configuration SHALL provide bounded retention through at least a maximum active-file size and a maximum backup-file count.

The existing `gateway.log` SHALL remain the stable human-oriented running log and SHALL NOT become the only diagnostic evidence surface for this feature.

#### Scenario: Gateway starts without diagnostic logging by default
- **WHEN** a gateway starts for a session whose gateway configuration does not enable diagnostic logging
- **THEN** the gateway keeps normal operation available
- **AND THEN** it does not create or append gateway diagnostic log entries merely because ordinary HTTP routes are called

#### Scenario: Enabled gateway writes bounded diagnostic files
- **WHEN** a gateway starts with diagnostic logging enabled and bounded rotation settings
- **THEN** the gateway writes diagnostic entries under the gateway-owned log directory
- **AND THEN** diagnostic log files rotate according to the configured maximum active-file size and backup-file count

### Requirement: Gateway diagnostic logs capture HTTP and mailbox failure evidence without raw sensitive content
When gateway diagnostic logging is enabled, the gateway SHALL record compact diagnostic entries for gateway HTTP requests and outcomes, including validation failures that occur before an endpoint handler is invoked.

Diagnostic entries for HTTP requests SHALL include at minimum method, path, status code, duration, request identifier, and diagnostic event code when those values are available.

Diagnostic entries for gateway mailbox facade operations SHALL include safe operational metadata such as operation name, transport, sender address, recipient addresses, generated message identifier when available, recipient count when available, result status, and repair guidance when applicable.

Diagnostic entries SHALL NOT include mailbox message body content, raw prompt text, attachment contents, authorization headers, cookie headers, bearer tokens, credential material, or environment secrets by default.

#### Scenario: Malformed mailbox send request is captured
- **WHEN** diagnostic logging is enabled
- **AND WHEN** a caller submits a malformed `POST /v1/mail/send` request that fails request-body validation before route handling
- **THEN** the gateway records a diagnostic entry for the failed HTTP request
- **AND THEN** the entry includes the route, status code, and normalized validation error locations
- **AND THEN** the entry does not include a mailbox body or raw request body dump

#### Scenario: Mailbox delivery failure records repair context safely
- **WHEN** diagnostic logging is enabled
- **AND WHEN** a gateway mailbox send reaches mailbox delivery but fails because mailbox-local state is unreadable or missing
- **THEN** the gateway records a diagnostic entry for the mailbox failure
- **AND THEN** the entry includes the operation, transport, safe participant metadata, error category, and repair hint when available
- **AND THEN** the entry does not include the message body or attachment contents

### Requirement: Gateway diagnostic logging deduplicates consecutive warning and error entries
When gateway diagnostic logging is enabled, the gateway SHALL deduplicate consecutive warning or error diagnostic entries that share the same semantic deduplication key.

The deduplication key SHALL ignore volatile values such as timestamp, duration, request identifier, and generated message identifier while preserving event code, route, HTTP status, error category, and normalized validation field paths.

The gateway SHALL write the first warning or error entry in a consecutive duplicate run normally, suppress later consecutive duplicates with the same key, and emit a summary entry with the suppressed count when the run ends or when diagnostic logging is flushed.

Diagnostic logging SHALL NOT deduplicate ordinary informational entries unless they are explicitly modeled as warning or error summaries.

#### Scenario: Consecutive equivalent validation errors are summarized
- **WHEN** diagnostic logging is enabled
- **AND WHEN** several consecutive requests fail with the same validation error shape on the same route
- **THEN** the gateway writes the first warning or error diagnostic entry
- **AND THEN** it suppresses later consecutive duplicates with the same semantic key
- **AND THEN** it emits a summary entry reporting how many duplicate diagnostics were suppressed

#### Scenario: Different error breaks a deduplication run
- **WHEN** diagnostic logging is enabled
- **AND WHEN** a warning or error diagnostic entry differs by route, status, event code, error category, or normalized validation field paths from the previous suppressed run
- **THEN** the gateway flushes the previous suppressed-count summary before recording the different diagnostic entry
