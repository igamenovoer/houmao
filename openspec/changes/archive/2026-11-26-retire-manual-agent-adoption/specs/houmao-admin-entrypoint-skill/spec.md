# Spec Delta

## ADDED Requirements

### Requirement: Admin entrypoint preserves actor frame and target gate
`houmao-admin-entrypoint` SHALL preserve `narrow-implicit` activation, intent-first classification, an immutable admin frame (`actor_kind=admin`, `verified_self_identity=null`), the explicit target gate, the `specialist-mgr` alias, distinct `pro` and `lite` routes, and rejection of `process-emails-via-gateway` in admin posture.

#### Scenario: Admin receives a manual session adoption request
- **WHEN** a human asks the admin entrypoint to adopt the current session into Houmao
- **THEN** the entrypoint explains that local lifecycle management requires a managed launch
- **AND THEN** the admin frame remains active and unchanged
- **AND THEN** the router continues to reject the agent-only `process-emails-via-gateway` route in that frame

## REMOVED Requirements

### Requirement: Admin entrypoint owns explicit joined-session adoption handoff
**Reason**: The packaged admin entrypoint no longer routes manual adoption.
**Migration**: Start a managed agent through the project launch route. Use the agent entrypoint in the resulting verified managed runtime.

### Requirement: Admin entrypoint preserves actor frame, target gate, and adoption invariants
**Reason**: The adoption handoff is retired.
**Migration**: Use the requirement Admin entrypoint preserves actor frame and target gate for the continuing admin routing contract.
