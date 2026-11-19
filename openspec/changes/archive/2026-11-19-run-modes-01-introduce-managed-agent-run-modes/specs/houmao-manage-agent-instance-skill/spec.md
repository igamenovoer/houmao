# Spec Delta

## ADDED Requirements

### Requirement: Instance launch guidance respects the requested or stored run mode

The packaged instance guidance SHALL use `--mode` for an explicit birth override and otherwise preserve profile or tool defaults across direct role, preset, dossier, and specialist launches. It SHALL direct the operator to the reported terminal or browser handoff and keep operator policy separate from mode.

#### Scenario: Default specialist launch

- **WHEN** a caller starts a Claude or Codex specialist without a selected mode
- **THEN** the example omits an override and describes the TUI handoff supplied by the launch result

#### Scenario: Profile selects a nonterminal agent

- **WHEN** a stored profile requests an available Web or service mode
- **THEN** launch does not add a terminal override and the instructions use the actual handoff or manager/gateway control reference

#### Scenario: Headless is requested

- **WHEN** an operator explicitly asks for a one-shot provider CLI
- **THEN** the guidance shows `--mode headless` and does not infer a headless selection merely from unattended automation

## REMOVED Requirements

### Requirement: `houmao-agent-instance` prefers TUI-supported launch posture when unspecified

**Reason**: The actual default and human handoff vary by tool.

**Migration**: Let project launch resolve the tool default or pass an explicitly requested mode.
