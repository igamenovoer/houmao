# Spec Delta

## ADDED Requirements

### Requirement: Project launches honor configured runtime and mailbox roots

Project-aware managed launch SHALL resolve runtime and mailbox placement from authorized explicit launch selections, then owner-side shared-root overrides, then selected overlay defaults. The launch SHALL record the effective placements in their existing runtime and mailbox bindings.

#### Scenario: Shared runtime and mailbox roots override an overlay default

- **WHEN** a project launch selects an overlay and supplies `HOUMAO_GLOBAL_RUNTIME_DIR` and `HOUMAO_GLOBAL_MAILBOX_DIR` without explicit placement overrides
- **THEN** runtime state and the configured filesystem mailbox use the selected shared roots

#### Scenario: An explicit shared mailbox root takes precedence

- **WHEN** a project launch specifies `--mail-root` and a different `HOUMAO_GLOBAL_MAILBOX_DIR`
- **THEN** filesystem mailbox binding uses the explicit shared mailbox root

#### Scenario: Project launch uses the overlay defaults

- **WHEN** an operator launches a project agent without shared-root overrides or explicit runtime and mailbox placement
- **THEN** the runtime and configured filesystem mailbox use their respective overlay defaults

### Requirement: Managed launch preserves its selected Houmao root context

Managed launch SHALL publish absolute paths for the execution binding's registry, any selected shared runtime and mailbox roots, and the selected overlay. It SHALL use `HOUMAO_GLOBAL_REGISTRY_DIR`, `HOUMAO_GLOBAL_RUNTIME_DIR`, `HOUMAO_GLOBAL_MAILBOX_DIR`, and `HOUMAO_PROJECT_OVERLAY_DIR` respectively. Relaunch SHALL retain this context from recorded launch authority.

#### Scenario: Web peers share a registry across different projects

- **WHEN** a DSH Web agent and a Kimi Web agent launch from different overlays with the same shared registry, runtime, and mailbox roots
- **THEN** their tmux environments and local tool shells carry the same shared selectors and their respective overlay selectors
- **AND THEN** `houmao-mgr agents global list` from either agent lists both peers from the selected registry

#### Scenario: Local placement keeps project-relative defaults

- **WHEN** an agent launches with overlay-local runtime and mailbox defaults
- **THEN** the selected overlay is published and the two shared-root selectors remain absent
- **AND THEN** self queries can read the effective agent bindings from the runtime manifest

#### Scenario: Relaunch uses the selected project context

- **WHEN** an operator relaunches an agent from a directory and environment that select different roots and another overlay
- **THEN** the agent receives the selectors recorded for its original execution and project context
