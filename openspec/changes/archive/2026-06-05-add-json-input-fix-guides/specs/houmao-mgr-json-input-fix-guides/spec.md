## ADDED Requirements

### Requirement: JSON input failures include schema and example fix guides
Maintained `houmao-mgr` subcommands that parse caller-supplied JSON from an inline option value, stdin, or a JSON file SHALL include a fix guide when JSON parsing or JSON shape validation fails.

The fix guide SHALL identify the failed command or operation, the input option or source, the root parse or shape problem, a JSON Schema-style expected shape, and at least one valid example payload or command invocation.

The primary error message SHALL remain concise and SHALL precede the schema and example so humans can quickly see the cause.

#### Scenario: Invalid inline JSON shows repair guide
- **WHEN** a maintained `houmao-mgr` subcommand accepts JSON through an inline text option
- **AND WHEN** the caller supplies syntactically invalid JSON
- **THEN** the command fails with a diagnostic that names the input option and parse error
- **AND THEN** the diagnostic includes a JSON Schema-style expected shape
- **AND THEN** the diagnostic includes a valid example payload or command invocation for that subcommand

#### Scenario: Valid JSON with wrong shape shows repair guide
- **WHEN** a maintained `houmao-mgr` subcommand accepts JSON through an inline text option, stdin, or a JSON file
- **AND WHEN** the caller supplies syntactically valid JSON whose structure does not match the command contract
- **THEN** the command fails with a diagnostic that names the shape problem in command-specific terms
- **AND THEN** the diagnostic includes a JSON Schema-style expected shape
- **AND THEN** the diagnostic includes a valid example payload or command invocation for that subcommand

### Requirement: JSON fix guides are command-specific and secret-free
JSON input fix guides SHALL be generated or selected from command-owned metadata rather than from generic parser prose alone.

Fix guides SHALL show only safe field names, enums, placeholder values, and command examples. They SHALL NOT echo credential material, OAuth tokens, API keys, bearer tokens, prompt text, mailbox message bodies, attachment contents, authorization headers, cookie headers, or environment secret values.

#### Scenario: Fix guide omits sensitive submitted values
- **WHEN** a JSON-input command fails while the submitted JSON includes secret-looking keys or values
- **THEN** the fix guide describes accepted keys and shape without printing secret material from the submitted payload
- **AND THEN** the example uses safe placeholder values rather than user-provided secrets

#### Scenario: Command metadata drives examples
- **WHEN** a JSON-input command has multiple accepted payload families or ids
- **THEN** the emitted schema and example match the selected family or id
- **AND THEN** the command does not emit a generic example for a different payload shape

### Requirement: Implementation inventories maintained JSON input surfaces
Implementation work for this change SHALL include a focused inventory of maintained `houmao-mgr` subcommands that parse caller-supplied JSON from inline option values, stdin, or JSON files.

The implementation SHALL bring in-scope JSON input surfaces under the fix-guide contract when they can provide a useful compact schema and example during this change. Surfaces that are file-only, test-only, demo-only, non-public, or require a larger design MAY be documented as out of scope.

#### Scenario: Inventory records covered and deferred surfaces
- **WHEN** the implementation work starts
- **THEN** the maintainer inventories maintained JSON input surfaces in the `houmao-mgr` command tree
- **AND THEN** the task evidence identifies which surfaces were covered by fix guides
- **AND THEN** any deferred surfaces have a short rationale
