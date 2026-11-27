# Design

## Context

The current launch resolver merges native aliases and typed settings over strategy defaults. DSH also assembles permission presets from setup values during home preparation. Hermes skips shared launch policy and sets command approvals during home construction. The Hermes ACP owner independently answers reverse permission requests. [Proposal](proposal.md) · [Launch Policy Engine](../../../src/houmao/agents/launch_policy/engine.py#L105) · [Hermes Configuration](../../../src/houmao/agents/hermes_configuration.py#L84)

The completed #104 change establishes native Hermes TUI admission, detached caller identity, signed mailbox access, and captured fixture authority. Those contracts form the baseline for this follow-up. [Issue #104 Change](../fix-hermes-managed-control-and-fixtures/proposal.md)

## Goals / Non-Goals

Enforce one operator-facing meaning for unattended mode across managed start and relaunch. Keep provider-specific permission projection and exact operation ownership in their existing adapters. The permission posture governs native approvals and sandbox settings within the selected execution owner. The launch's tool availability, credential selection, and Houmao gateway authorization remain separate.

## Decisions

### Validate the Resolved Permission Posture Before Startup

Resolve the effective authored values through the existing setup, specialist, profile, and launch layers. Normalize supported native aliases before comparing the winning permission fields with the qualified unattended values. Accept matching values and supply the qualified value for each omission. A conflict reports the setting, its source, the provider and mode, and the required value. Check before provider startup, runtime-home policy mutation, or replacement of a live owner. The previous merge accepted a restricted sandbox or an interactive approval under the unattended label. An explicit error preserves the operator's stated permission limit.

Use `bypassPermissions` for Claude, `never` and `danger-full-access` for Codex and DSH, and native `auto` for Kimi. Kimi's headless `-p` selects `auto` itself. On interactive backends, Kimi's `auto` resolves routine tool approvals before the rules that can still prompt in `yolo`. Select the existing qualified strategy for the executable and apply the same effective values through all provider-start surfaces. [Supported Modes](../../../src/houmao/agents/realm_controller/run_modes.py#L19) · [Kimi Tool Parameters](../../../src/houmao/agents/tool_params/kimi.py#L36)

Carry that validated posture through private home projection and final provider arguments. Include generated launch helper arguments passed at invocation. Pass explicit effective permissions through DSH home preparation and Web owner startup so neither falls back to a narrower setup preset. Record the mode, effective values, and source in existing launch diagnostics. `as_is` still applies supported authored choices and the native baseline for omissions. When changing postures on explicit relaunch, distinguish previous Houmao projections from operator-authored values. Observation, resume-only control, and gateway reattachment read the current posture.

### Apply the Native Hermes Policy Before Readiness

Resolve Hermes posture before building its home, and apply the same policy at provider start using the resolved launch record. Update only the managed approval keys under the existing provider-home mutation boundary. Unattended homes carry string-valued `approvals.mode: "off"` and `approve` for single-query and unattended contexts. As-is uses the current manual and deny baseline for omitted settings. Record the effective projection without credentials or approval contents. Use the selected PATH executable and qualify the supported behavior against stock Hermes and its authenticated native connection. For a same-home daemon, establish that the qualified policy governs the managed conversation before advertising unattended readiness. Use existing relaunch and scoped cleanup authority if startup requires replacement.

One private-home projection covers command approvals in TUI, service, and headless modes. An Ink flag is scoped to the viewer or session creation, while Houmao preselects the conversation before launching its viewers and headless clients. Keep exact native session selection and finite continuation. Preserve provider-enforced hard denials, including incomplete hardline scans. Use the same managed policy in the generated Hermes helper and the Hermes fixture paths that exercise it. [Native Hermes Client](../../../src/houmao/agents/realm_controller/backends/hermes_native.py#L457) · [Launch-Plan Policy Branch](../../../src/houmao/agents/realm_controller/launch_plan.py#L306)

### Apply ACP Edit Mode and Qualify Remaining Tool Permissions

After binding the exact service session, select and verify its advertised broadest edit mode, `dont_ask` in qualified Hermes v0.23.4. Establish the mode on fresh bind and exact relaunch before readiness. Use the provider's session-level setting so the editor policy governs native file tools where they run. Retain enough private provenance to return a prior managed edit projection to the as-is baseline at a later provider start. A missing capability or failed mode change fails unattended startup with a scoped diagnostic.

Hermes can still relay tool-permission requests through ACP. Select the advertised one-time option only when the request identifies a supported tool permission for the exact bound session and current, uncancelled owner operation. Validate the native request shape and reject ambiguous or stale options. Use a bounded rejection or cancellation for a clarification, a model setting confirmation, a missing one-time option, or an unrecognized interaction. A one-time tool grant addresses the current request and keeps session-wide and permanent reverse grants out of the handler. [Hermes ACP Owner](../../../src/houmao/agents/realm_controller/backends/hermes_acp_service.py#L99)

### Project Current Hermes Approval Evidence

Use the authenticated pinned `session.resume` snapshot already used for readiness. Filter the pending approval entries by active execution generation. Project `control.approval_pending` as true for a verified pending approval, false for a current verified snapshot with none, and null for unqualified evidence. Use the shared observation for manager and gateway state and show a readable approval wait in manager output. Keep ordinary admission closed during the wait and allow the existing native Ink interaction or exact cancellation to settle it. Only publish the boolean, even if the native payload contains commands, questions, or sensitive content. [Hermes Observation](../../../src/houmao/agents/realm_controller/backends/hermes_tui.py#L753)

### Use the Mail-List Schema for Public Validation Guidance

Use the trusted route template after the existing admission boundary to identify offline or online mail-list validation. Keep HTTP 422 and the `detail` entries. Retain schema-declared field names in `loc`. Use the body-level location for arbitrary extra keys and include a fixed hint about accepted fields, including `read_state: "unread"`. Use static schema metadata for that hint. Request values, arbitrary key strings, raw validator messages, and decode context stay out of HTTP responses and diagnostic logs. The diagnostic summary and its deduplication remain independent of the public hint. [Validation Handler](../../../src/houmao/agents/realm_controller/gateway_service.py#L11121) · [Mail-List Schema](../../../src/houmao/mailbox/models.py#L168)

### Route Native Hermes Skill Lookup Through the Public Roots

Update notifier guidance and ordinary mailbox prompt guidance to tell Hermes to open the public `houmao-agent-entrypoint` using `skill_view` by name. Supply the existing route, gateway URL, channel, and expected binding ID where the operation requires them. The installed entrypoint verifies self and passes the actor frame to `houmao-shared-routines`. That sibling can direct Hermes to its selected relative child file through native parent-relative lookup. Keep the child path within the installed parent instructions. Use the existing API fallback when either required public root is absent. The fixture role uses `process-emails-via-gateway` for notifier rounds and `agent-email-comms` for ordinary mail. [Notifier Skill Guidance](../../../src/houmao/agents/realm_controller/gateway_service.py#L8066) · [Entrypoint Routes](../../../src/houmao/agents/assets/system_skills/public/houmao-agent-entrypoint/SKILL.md#L25)

## Risks / Trade-Offs

- Profiles that currently rely on a narrower setting under the default unattended mode will fail preflight. The error identifies the setting and points to `as_is`.
- A configured native approval field may be accepted syntactically but fail to govern one execution surface. Verify the effective provider posture for each supported mode and verify ACP's bound native edit mode.
- Approval snapshots can lag a settlement or describe a different conversation. Require current identity and execution-generation evidence, and retain unknown state when it cannot be verified.
- A generic validation location can contain request-controlled strings. Derive public mail-list guidance from the admitted route and the known schema.

## Migration Plan

Apply common launch validation and then qualify Hermes launch, relaunch, state, and ACP behavior. Apply the gateway and skill updates before the live mail checks. Existing live runtimes enter the new posture on explicit relaunch. Profiles with intentional restrictions select `as_is` before their next start. Clients can treat the approval indicator and validation hint as optional response fields. Consumers that reject unknown fields need the matching response schemas.
