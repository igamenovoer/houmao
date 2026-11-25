# Design

## Context

The [proposal](proposal.md) covers the symptoms observed in the live skill-update test. The completed `define-built-in-agent-permissions` change defines explicit signer selection, default-group authorization, and managed-self scheduling. These diagnostics use those decisions as inputs.

The access CLI already returns the policy revision, roster mode, and configured default group. The file CLI verifies `/v1/endpoint` before selecting a signer. The gateway already returns a reason code in `detail.error_code`, which the client currently drops for HTTP 401 and 403. The strict push receipt describes saved candidates, publication, activation, and readiness. The public landing page already consults the endpoint mode to qualify Web entry.

## Goals / Non-Goals

**Goals**

- Place reliable context and a next action beside the outcome that prompted it.
- Keep policy decisions and publication receipts authoritative. Keep existing HTTP status and payloads, CLI stdout and exit behavior, and structured state compatible with existing callers.

**Scope Boundaries**

- Use explicit signer selection and the existing first-admin ceremony. A generated-key enrollment command and private-key recovery belong to a follow-up.
- Keep default-group details in the verified owner view and enrollment details in `access list`. Public dashboard data comes from the endpoint descriptor.

## Decisions

### Use the Committed Snapshot for Grant Feedback

Have the existing owner-policy mutation path in `srv_ctrl/commands/agents/access.py` render command-specific guidance from the same snapshot it emits in the receipt. Report the successful row change and explain open admission at that revision. A grant recorded in open mode can affect later keyed admission. Labeling the write a no-op would hide that fact. For keyed mutations, refer to `access explain` for the exact principal, resource, and action. A direct row alone cannot establish the live decision because other permission sources and provider prerequisites also apply.

Use the initialized snapshot for the open-roster enrollment hint, including when `access init` returns an existing policy. Explain the verified attached gateway prerequisite for `admin-add --first`. Keep the existing owner-local initialization path available for detached targets.

### Use Verified Mode and Bounded Refusal Reasons

Add missing-signer guidance at the existing file command check, after target and listener verification. Show `--signer` on the `files` group before `mounts`, `read`, or `push`. Preserve the existing explicit caller modes, including `--unsigned`. A hidden owner-admin fallback would change caller attribution and could authorize a publication the original caller could not perform.

Extend the gateway client's internal HTTP error with an optional recognized reason. Limit decoding to bounded 401 and 403 responses of the existing error shape and accept known file-access codes only. Retain the existing generic detail when the body is malformed, oversized, or unfamiliar. Use the file route contract and validated request to render the attempted action and mount where present. Mount discovery has no single resource. Describe the caller by selection mode when it has no independently verified principal, and direct the owner to `access explain` for an insufficient-authority diagnosis. This gives a remote caller useful context without echoing raw peer data or changing the gateway response.

### Render Busy Recovery Beside the Receipt

Emit the existing push result first. For a confirmed busy receipt, use stderr to give a next action. Suggest an explicitly requested `--when-idle` push only when the CLI is in `agents self` and the receipt confirms managed-self attribution. `--self-signer` selects a stable peer key, and an unsigned self request has anonymous provenance. Other callers receive advice to retry once the target is ready. Each explicit retry uses the saved candidate, recorded base, and a fresh operation ID.

Keep machine-readable outcomes tied to the receipt. Adding even an optional HTTP `hint` field would make older strict receipt readers reject it. An unconfirmed attempt remains inspectable through its original operation ID and a queued intent follows its existing handoff and status path.

### Render Policy Summary at the Appropriate Boundary

For human `agents single state`, lazily read the owner snapshot in the plain and fancy renderers. Match the already selected local record and verify its owner binding and generation. Render normal state even if verification fails. The typed state result serves passive, executor, and machine consumers, so keep the extra information in the CLI view and bypass the lookup when that view is unused.

For the dashboard, derive mode and policy eligibility from one current endpoint observation for the verified target. Use the same mode for the summary and entry copy. Require the existing origin and native availability checks for the action and leave `/v1/web/enter` responsible for the current decision when the browser follows it. The page already renders read-only with bounded public data, so avoid moving owner access inspection to it.

## Risks / Trade-offs

- **Stale diagnostics** → Identify the mutation's committed revision. Treat a dashboard observation as display evidence and apply live policy when the user acts.
- **Untrusted gateway details** → Keep response decoding bounded and allowlisted. Render only the attempted effect and safe caller context. Keep private signer paths, request contents, and enrollment inventories out of file diagnostics.
- **Mixed output** → Send mutation, refusal, and busy guidance to stderr. Test stdout and exit status separately to preserve the manager's machine-readable interface.

## Migration Plan

The CLI can consume the current gateway responses. Update the CLI, packaged guidance, and dashboard through the normal release path. Older clients can still consume the current routes and receipt shapes.
