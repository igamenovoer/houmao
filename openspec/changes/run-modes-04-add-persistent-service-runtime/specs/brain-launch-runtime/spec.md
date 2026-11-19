# Spec Delta

## MODIFIED Requirements

### Requirement: Unattended DSH Launch Composes Coherent Permission Presets

When a managed DSH headless, service, or Web launch applies unattended operator policy, profile generation SHALL register a matching unattended preset in the native permission-presets service and select it as the default preset alongside matching approval and sandbox-policy defaults so native permission-service activation succeeds without preset-mismatch errors. Launches in `as_is` operator mode SHALL omit unattended permission, approval, and sandbox-policy overrides.

#### Scenario: Unattended Launch Activates Native Permission Service Cleanly
- **WHEN** a managed DSH native headless, ACP service, or Web agent starts in `unattended` operator mode
- **THEN** the generated profile patch configures a named unattended permission preset alongside DSH's standard presets, sets it as `defaultPreset`, and aligns `approval` and `sandbox-policy` with that preset
- **AND THEN** DSH starts without a `permission` plugin preset-mismatch activation error in stderr

#### Scenario: As-Is Launch Preserves Native Permission Defaults
- **WHEN** a managed DSH agent starts in `as_is` operator mode
- **THEN** the generated profile patch omits unattended `permission`, `approval`, and `sandbox-policy` overrides so native interactive approval behavior remains active
