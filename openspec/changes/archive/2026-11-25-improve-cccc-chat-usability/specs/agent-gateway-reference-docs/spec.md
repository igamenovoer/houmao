# Spec Delta

## ADDED Requirements

### Requirement: Gateway Reference Documents Web and Headless Prompt Readiness

The gateway reference SHALL document how an authorized driver uses `GET /v1/status` to observe prompt readiness for Web and headless agents. The procedure SHALL distinguish gateway health, managed prompt readiness, and plugin connection, and SHALL describe the readiness snapshot as preflight evidence for a later admission decision.

#### Scenario: Driver Checks Either Surface Before a Prompt

- **WHEN** a driver reads the readiness procedure for an attached managed Web or headless agent
- **THEN** it learns to check for a healthy gateway and a current `observation` with `can_accept_prompt_now: true`
- **AND THEN** it can find Web details under `web` and headless diagnostics at `GET /v1/control/headless/state` by selecting the known surface

#### Scenario: Readiness Evidence Is Missing or Changes

- **WHEN** the driver has missing, stale, or unknown readiness evidence, or the body becomes busy after a ready observation
- **THEN** the procedure treats missing or stale evidence as unconfirmed and explains that each prompt or ordinary event is subject to live admission at handoff

#### Scenario: CCCC Driver Checks Its Setup

- **WHEN** a CCCC driver checks readiness for an ordinary chat exercise
- **THEN** the CCCC guide links to the gateway procedure and explains how to verify the selected CCCC binding and its connection independently

### Requirement: Gateway Plugin Guides Report Declared Compatibility

The CCCC integration and gateway plugin author references SHALL report gateway SDK compatibility and Houmao dependency constraints consistent with the distributions they document. The CCCC reference SHALL identify the CCCC external-receiver protocol version separately from the gateway SDK version.

#### Scenario: Operator Checks CCCC Installation Requirements

- **WHEN** an operator consults either reference to install the current optional CCCC package or the example plugin
- **THEN** the reference reflects the corresponding SDK and Houmao dependency declarations and identifies their source
- **AND THEN** the CCCC reference identifies the separate provider protocol required for receiver qualification
