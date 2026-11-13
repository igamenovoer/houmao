## REMOVED Requirements

### Requirement: Agents self exposes effective system prompt retrieval
**Reason**: This public command existed to let the deleted Kimi auto skill retrieve its own prompt and has no remaining maintained consumer.

**Migration**: Inspect managed prompt provenance through brain and runtime inspection surfaces; providers receive prompts through native launch-time projection.

### Requirement: Self system prompt command is safe for auto-skill use
**Reason**: Houmao no longer supports auto-skill role injection or a public self-prompt retrieval workflow.

**Migration**: Remove invocations of `houmao-mgr agents self system-prompt show`; rebuild Kimi brains so role delivery uses native `SYSTEM.md`.
