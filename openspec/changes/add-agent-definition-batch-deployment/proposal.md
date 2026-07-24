## Why

After single Agent Definition deployment is reliable, users need to request several project deployments from one exact definition while delegating limited choices such as names, compatible tools, and existing credential references. The operation needs complete preflight and one visible outcome without creating a second long-lived lifecycle for a batch object.

This change depends on `deploy-predefined-agent-blueprints`.

## What Changes

- Add a Batch Deployment Request that records the requested count, shared typed inputs, optional per-member overrides, and explicit delegation categories.
- Add a Batch Deployment Plan containing one fully validated member plan per requested deployment.
- Require names to be unique, tools to satisfy the definition contract, and credentials to resolve only to existing compatible references.
- Treat a plural count as quantity only. It does not authorize delegated choices.
- Apply the batch through staged content, one catalog visibility transaction, and recoverable operation state.
- Record one batch operation identifier and member ordinal on each ordinary Agent Deployment.
- Do not add a durable Agent Deployment Batch domain object, nullable membership graph, or independent batch update and removal lifecycle.
- Preserve independent member inspection, doctor, update, launch, and removal after successful apply.
- Route plural deployment through the existing `houmao-agent-definition` routine and admin entrypoint.

## Capabilities

### New Capabilities

- `houmao-mgr-agent-definition-batches`: Defines batch requests, delegated selections, member planning, staged apply, recovery, and provenance.

### Modified Capabilities

- `houmao-manage-agent-definition-skill`: Adds bounded plural deployment to the existing definition routine.
- `houmao-admin-entrypoint-skill`: Routes explicit plural Agent Definition deployment without implying launch.
- `houmao-shared-routines-skill`: Exposes the plural route under admin posture.
- `project-config-catalog`: Correlates ordinary Agent Deployments through a batch operation identifier without adding a batch domain object.

## Impact

The change affects Agent Definition deployment commands, planning and staging, catalog migrations, system-skill routing, behavior tests, and deployment documentation. It does not create managed-agent instances, credentials, or private workspaces.
