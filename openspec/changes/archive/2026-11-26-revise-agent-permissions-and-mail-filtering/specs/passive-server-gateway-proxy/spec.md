# Passive Server Gateway Proxy Delta

## MODIFIED Requirements

### Requirement: Passive Administration Updates the Retained Default Directly

`PUT /houmao/agents/{agent_ref}/admin/default-permission-group` SHALL use the gateway setter's request and result contract. Passive ingress SHALL authorize `admin.default-group.set` on `policy` for the verified retained target and recheck current effective `agent-admin` authority at commit. The route SHALL write to the owner's retained policy without a live gateway.

#### Scenario: A passive admin updates a stopped target

- **WHEN** passive ingress admits a default-group request under effective admin authority for a stopped target with verified retained policy
- **THEN** the passive server commits the group and reports its revision without forwarding to a gateway or starting the target
- **AND THEN** later gateway and passive calls use the same retained policy

#### Scenario: Passive ingress receives an unqualified request

- **WHEN** the caller lacks effective admin authority, supplies invalid proof, or the passive server cannot verify the retained owner and policy
- **THEN** the request fails before mutation
- **AND THEN** the passive server uses neither its backing credential nor another target's policy as authority

## ADDED Requirements

### Requirement: Passive Administration Updates a Principal’s Fallback Directly

`PUT /houmao/agents/{agent_ref}/admin/principals/{principal_id}/default-fallback` SHALL use the gateway setter's contract. Passive ingress SHALL authorize `admin.default-fallback.set` on `policy` for the verified target and recheck effective `agent-admin` authority before it commits the setting, revision, and audit record in the retained policy.

#### Scenario: A passive admin disables fallback for a detached agent

- **WHEN** an authorized passive request disables fallback for an enrolled principal on a verified target with no attached gateway
- **THEN** the mutation commits on the retained target without starting its body
- **AND THEN** both later passive admission and its next attached gateway use the committed setting for that verified principal

#### Scenario: Passive ingress cannot revalidate the caller

- **WHEN** the caller's admin authority or the verified retained target becomes invalid before commit
- **THEN** no fallback setting changes and no substitute backing authority is used
