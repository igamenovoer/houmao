## MODIFIED Requirements

### Requirement: Demo startup SHALL reuse the tracked mailbox-demo fixture family and launch one managed headless Claude participant plus one managed headless Codex participant through demo-owned `houmao-server`
The tracked default startup flow SHALL:

- use `tests/fixtures/agents` as the default agent-definition root unless `AGENT_DEF_DIR` overrides it
- reuse the tracked dummy-project fixture family defined for narrow runtime-agent flows
- provision copied dummy-project workdirs under `<output-root>/projects/initiator/` and `<output-root>/projects/responder/`
- build a Claude brain manifest from the tracked preset `tests/fixtures/agents/roles/mail-ping-pong-initiator/presets/claude/default.yaml`
- build a Codex brain manifest from the tracked preset `tests/fixtures/agents/roles/mail-ping-pong-responder/presets/codex/default.yaml`
- preserve each tracked participant preset `launch.prompt_mode` when building those brain manifests
- start one demo-owned `houmao-server` under `<output-root>/server/`
- start that demo-owned `houmao-server` in no-child mode for the native managed-headless startup path
- launch one managed headless Claude Code participant and one managed headless Codex participant through the managed-agent headless launch surface
- use explicit demo-specific initiator and responder role names from the same agent-definition root
- place both participants on one shared mailbox root under `<output-root>/mailbox/`
- attach a gateway for each participant after launch
- enable gateway mail-notifier polling for each participant

The tracked default implementation in this change SHALL support the headless/headless participant pairing only. Unsupported transport selections SHALL fail clearly before live run work begins.

The demo SHALL rely on the runtime-owned mailbox system skill for mailbox operations rather than requiring participant-specific mailbox transport instructions from legacy recipe files.

Because the startup flow uses native managed-headless Houmao routes rather than `/cao/*` compatibility session control, demo startup readiness SHALL depend on Houmao-server root health and SHALL NOT require child-CAO health.

When a tracked participant preset requests unattended operator prompt mode, the built brain manifest SHALL retain that mode and the later live managed-headless launch SHALL expose launch posture evidence consistent with unattended rather than silently falling back to interactive posture.

#### Scenario: Successful start yields two managed headless participants with built manifests and attached gateways
- **WHEN** a developer runs `scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh start` with prerequisites satisfied
- **THEN** the run root contains copied dummy-project workdirs for the initiator and responder
- **AND THEN** the demo builds and records one tracked Claude manifest and one tracked Codex manifest before launch
- **AND THEN** those manifests retain the tracked participant preset operator prompt mode when one was declared
- **AND THEN** the demo starts one managed headless Claude participant and one managed headless Codex participant through demo-owned `houmao-server`
- **AND THEN** both participants resolve to the shared mailbox root under the selected output root
- **AND THEN** both participants report attached gateway state with notifier control available

#### Scenario: Startup does not require child-CAO health for the headless demo-owned server
- **WHEN** the demo-owned `houmao-server` is started in no-child mode for the tracked headless/headless startup path
- **THEN** the start command treats Houmao-server root health as sufficient startup readiness
- **AND THEN** the demo does not fail solely because no child `cao-server` is running

#### Scenario: Unattended recipe launch posture survives into the live managed-headless launch
- **WHEN** a tracked participant preset for this demo requests `launch.prompt_mode: unattended`
- **THEN** the corresponding built brain manifest records `launch.prompt_mode: unattended`
- **AND THEN** the later live managed-headless participant records unattended live launch posture rather than silently using interactive posture
