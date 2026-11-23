# Spec Delta

## MODIFIED Requirements

### Requirement: Kimi service negotiates its own ACP capabilities

Kimi service SHALL admit eligible versions at or above 2.6.0 and start `kimi acp` over owner-private stdio with the selected home, workspace, environment, and operator policy. The adapter SHALL verify the protocol and executable identity, record the actual peer version and capabilities, and advertise only client capabilities within the owner's authority.

#### Scenario: A maintained Kimi ACP build starts

- **WHEN** a build at the minimum or above initializes and binds the selected session successfully
- **THEN** the service becomes ready with the actual Kimi version and capabilities and no terminal or Web handoff

#### Scenario: A requested capability is unavailable

- **WHEN** the selected Kimi build lacks a required session operation or asks for an unsupported client facility
- **THEN** the adapter reports the limitation without invoking a different mode or granting undeclared access

#### Scenario: A newer ACP peer fails protocol or identity verification

- **WHEN** an eligible executable starts and the peer reports an unsupported protocol or a version inconsistent with the selected executable
- **THEN** startup reports the failed verification and withholds readiness
