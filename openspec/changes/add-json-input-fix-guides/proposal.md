## Why

Agents and operators can pass syntactically valid JSON to `houmao-mgr` subcommands and still receive missing-field errors that do not explain the expected JSON shape. This causes callers to retry shell quoting when the real fix is to change the JSON structure.

## What Changes

- Add a reusable diagnostic contract for `houmao-mgr` subcommands that accept JSON strings, stdin JSON, or JSON files as input.
- Require JSON-input failures to include a fix guide with the failing input option, a JSON Schema-style expected shape, and a valid command-specific example.
- Apply the contract to `houmao-mgr internals config-drafts generate --intent`, including the current `fields` wrapper requirement and supported fields for the selected draft id.
- Preserve concise normal output and existing successful command behavior.
- Do not expose secret credential material, mailbox bodies, prompt text, or other sensitive values in generated fix guides.

## Capabilities

### New Capabilities
- `houmao-mgr-json-input-fix-guides`: Cross-command diagnostics for `houmao-mgr` JSON input surfaces, including schema and example guidance on failure.

### Modified Capabilities
- `houmao-mgr-config-drafts`: `generate --intent` failures shall explain the expected intent JSON shape for the selected draft id and include a valid example.

## Impact

- Affected code: JSON input loading and validation helpers under `src/houmao/srv_ctrl/`, starting with `src/houmao/srv_ctrl/config_drafts/rendering.py` and `src/houmao/srv_ctrl/commands/internals.py`.
- Affected CLI surfaces: `houmao-mgr internals config-drafts generate --intent`; implementation should inventory other maintained `houmao-mgr` JSON input options and either bring them under the shared contract or document why they are out of scope.
- Affected tests: focused unit tests for config-draft JSON shape errors, invalid JSON, unsupported fields, missing required fields, and any shared JSON fix-guide formatter.
- Affected docs and skills: CLI reference and packaged `houmao-agent-definition` guidance where they show JSON intent examples for config drafts.
