## ADDED Requirements

### Requirement: Verified fixed-loopback CAO replacement SHALL continue across known launcher configs
When the interactive demo is replacing a verified local `cao-server` on `http://127.0.0.1:9889`, it SHALL treat launcher-stop attempts against known configs as a search for the config that owns the live service rather than assuming the first candidate must succeed.

If one known-config launcher-stop attempt fails to produce usable structured output but the fixed loopback target is still listening and later known configs remain available, the demo SHALL continue trying later known configs before declaring replacement failure.

If all known configs are exhausted and the fixed loopback service is still listening, the demo SHALL fail explicitly and SHALL NOT create an active interactive state artifact.

#### Scenario: Fresh current config does not block replacement of an older verified CAO owner
- **WHEN** a developer starts the interactive demo and launcher `status` verifies a healthy local `cli-agent-orchestrator` service on `http://127.0.0.1:9889`
- **AND WHEN** the current run's fresh launcher config does not own that live service
- **AND WHEN** a launcher `stop` attempt for the fresh config does not produce usable structured output
- **AND WHEN** a later known launcher config does own the verified live service
- **THEN** the demo continues to the later known config instead of aborting on the first stop attempt
- **AND THEN** the verified fixed-loopback `cao-server` is replaced before interactive session startup continues

#### Scenario: Exhausted known configs fail safely
- **WHEN** a developer starts the interactive demo and launcher `status` verifies a healthy local `cli-agent-orchestrator` service on `http://127.0.0.1:9889`
- **AND WHEN** every known launcher config fails to stop that verified live service
- **AND WHEN** the fixed loopback target is still listening after the known-config replacement attempts finish
- **THEN** startup fails with an explicit replacement diagnostic
- **AND THEN** the demo does not write `state.json` as active
