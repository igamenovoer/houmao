## MODIFIED Requirements

### Requirement: Automatic mailbox roundtrip testing SHALL use the direct live-agent mail path
Automatic testing that claims to satisfy the direct live-agent mailbox contract SHALL start two actual local agents and perform mailbox send, check, and reply operations through the direct live-agent mail path, not through fake mailbox injection, not through gateway transport commands, and not through fake CLI stand-ins.

The qualifying automatic path SHALL resolve the actual local `claude` and `codex` executables together with real credential profiles selected by the tutorial-pack blueprints or explicit autotest-harness overrides.

Fake executables, deterministic stand-ins, or synthetic credential stores MAY remain useful for regression coverage, but they SHALL NOT satisfy this requirement even when they reuse the same underlying tutorial-pack flow.

#### Scenario: Real-agent harness uses actual local tools and credential profiles
- **WHEN** the tutorial pack executes its canonical `autotest/run_autotest.sh` case
- **THEN** it starts the sender and receiver through the normal `start-session` path using the actual local `claude` and `codex` tools
- **AND THEN** it resolves real credential material for both participants before the live roundtrip begins
- **AND THEN** it performs mailbox operations through the direct runtime mail path without gateway or fake-mail shortcuts

#### Scenario: Stand-in live coverage is not sufficient for the direct-live contract
- **WHEN** a deterministic harness reports a successful mailbox roundtrip while using fake `claude`, fake `codex`, fake credential material, or any other stand-in agent surface
- **THEN** that result does not satisfy the direct-live automation requirement
- **AND THEN** the real-agent harness requirement remains failing until the actual local tools produce the inspectable mailbox artifacts
