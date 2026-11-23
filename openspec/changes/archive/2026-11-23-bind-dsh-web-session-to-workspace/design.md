# Design

## Context

The DSH Web companion already owns native Agent creation, exact resume, and in-place reset. It supplies the launch cwd and publishes an execution identity. DSH stores Workspace membership separately and uses it for navigation. Native browser sign-in exchanges the launch token for a browser cookie at the root and redirects to a clean URL. [Managed companion](../../../src/houmao/agents/assets/dsh/managed-web.mjs) · [DSH browser authentication](../../../extern/orphan/deepseek-harness/packages/host/authentication-token/src/browser-auth.ts)

## Goals / Non-Goals

**Goals**

- Make membership part of publishing a ready managed DSH Web session.
- Select the published session on entry before browser startup can create another conversation.

**Non-Goals**

- Changes to DSH's general directory picker, first-use policy, or other run modes.
- Changes to the gateway roster, ticket, or browser authentication contracts.

## Decisions

### Attach the Native Session Before Publishing the Managed Binding

Use the native Workspace registry to create or reuse the canonical launch directory. Compose Workspace attachment with the companion's existing Agent setup. DSH registers the Session before invoking setup and publishes the Agent after setup succeeds. Verify the target ID and Workspace membership there. The native registry deduplicates canonical paths, and attachment checks the exact session header's cwd. [Workspace registry](../../../extern/orphan/deepseek-harness/packages/workspace/workspace/src/index.ts) · [Session attachment](../../../extern/orphan/deepseek-harness/packages/workspace/workspace/src/entity.ts) · [Native Agent setup](../../../extern/orphan/deepseek-harness/packages/core/agent-loop/src/index.ts)

Share this step across new launch, exact resume, and in-place reset. Keep the current Agent lifecycle so preset, model, role, and receipt reconciliation run through their established paths. Exact resume uses the retained ID. Each explicit replacement uses its own ID, and retries within that attempt use the same candidate. Leave previous and unrelated native history intact. A setup failure returns the existing redacted lifecycle error and withholds the new ready binding. Native persistence may retain a record for the failed candidate. Resolve uncertain results against that candidate before repeating a mutation.

### Resolve the Browser Target Before Native Startup Selection

Reuse the gateway's verified entry binding and DSH's native cookie exchange. Carry an owner-verified target for that entry through native authentication. The target identifies the Workspace and the existing managed session from the live execution. The native browser consumes it once before ordinary restoration can issue a create request. Later navigation and reload use native browser selection. Status, dashboard rendering, and reconnect remain read-only.

DSH already supports authenticated index bootstrap data through `webserver/index-inject` and exact selection through `uiWorkspace.openSession`. Liveshare demonstrates opening a catalogued session once. DSH rc.1 and rc.3 expose those pieces. Their stock Workspace restoration can still start a create request while an extension waits for the session catalog, and native root authentication clears the query. Qualify a supported startup ordering mechanism under the managed Web profile at the existing version floor and on a newer supported build. If the extension points cannot provide that ordering, record the browser work as blocked on a supported DSH startup hook. [Index injection](../../../extern/orphan/deepseek-harness/packages/host/webserver/src/index.ts) · [Native exact selection](../../../extern/orphan/deepseek-harness/packages/experimental/liveshare/src/client/viewer-session.ts) · [Stock restoration](../../../extern/orphan/deepseek-harness/packages/client/ui-workspace/src/client/navigation.ts) · [Version policy](../../../src/houmao/agents/launch_policy/registry/dsh.yaml)

## Risks / Trade-offs

- A post-startup selection can hide an extra blank session. Qualify a fresh entry before the first turn and an exact relaunch after a turn. Check native inventory and startup mutation calls as well as the displayed selection.
- Managed authority can change across authentication or lifecycle work. Recheck the live execution and membership at handoff and accept only the current verified target. A stale or unavailable target surfaces a safe entry error.
- Workspace reuse may encounter user-created state in the same native home. Use native deduplication and attachment, preserve existing records, and test with an unrelated Workspace and conversation.

## Migration Plan

Use explicit exact relaunch to publish Workspace membership for an existing managed session. The native registry retains its records and conversation history across Houmao upgrades.
