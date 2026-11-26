# Design

## Context

`gateway/authorization.py` already evaluates exact domain, resource, and action rows with PyCasbin. A gateway listener and the passive server resolve the same retained target policy. The admin roster selects open or keyed admission independently of the proof type. The owner-local CLI already edits policies and enrolls stable SSH credentials.

The launcher already provisions a generation-specific `self` key on disk before native startup. All-interface gateway startup checks that binding, and `agents self refresh` omits proof when it contacts a keyed gateway. The existing versioned file provider handles skills. Native refresh observes and reconciles current skills and MCP, while approval of a replacement remains an update-provider responsibility.

The current `agent.prompt` action covers both `submit_prompt` in the durable gateway queue and direct prompt control. The queue also recognizes certain slash commands. The public prompt renderer already quotes input behind a gateway-authored header, and AG-UI already constructs a structured task prompt. These are starting points for a private work-request path.

Incoming mail currently bypasses Bob's gateway policy. Offline registry admission authenticates the sending member and resolves recipients. Standalone filesystem delivery and provider delivery can write to a mailbox through different transport paths. All paths reaching a policy-governed inbox need the same recipient-side decision.

## Goals / Non-Goals

**Goals**

- Let a newly reachable agent make ordinary contact without per-recipient enrollment. Give admins one target setting for unassigned callers, while retaining explicit assignments for recognized callers.
- Explain the resulting access on the target, including incoming mail while the gateway is detached.
- Keep authenticated caller provenance stable across transports and policy transitions. Preserve the exact native effect and original authorization evidence through handoff.
- Let short-lived CLI calls use a generation-scoped signer that follows the running agent. Keep gateway attachment optional.

**Non-Goals**

- Provider-native package installation, gateway plugin installation, and filesystem or execution-owner delegation through agent policy.
- General custom-role inheritance, wildcard grants, a separate gateway ingress router, or changes to native maintenance readiness.

## Decisions

### Resolve Built-In Roles Through the Existing Target Policy

Use `managed-self` and `agent-admin` as the two system-controlled memberships. `agent-admin` names the same group called `gateway-admin` in the existing protocol and records. Keep one catalog entry for that authority. Public admission remains a deployment-controlled endpoint baseline. Preserve the existing actor kinds for attribution.

An initialized empty roster uses open-admin admission while preserving caller provenance, including signed managed-self provenance. In keyed mode, direct roster qualification belongs to the exact key. The first and last admin transitions retain the roster revision and open epoch. Invalid supplied proof fails. All supported effects retain their target, capability, and native readiness checks.

Use the `builtin:` namespace for owner-assignable role references. Preserve existing local roles and assignments, including names that collide with the catalog. Report a reserved-name collision before accepting an ambiguous new assignment. Pin the selected catalog version. Future revisions require an explicit reassignment to add effects to that version. The evaluator expands each built-in to the exact rows below. Owners retain their existing custom role operations.

| Assignable role | Included access | Added effects |
| --- | --- | --- |
| `builtin:agent-observer` | Public baseline | `agent.status.read` on `agent` |
| `builtin:agent-requester` | Observer | `agent.mail.deliver` and `agent.request.submit` on `agent` |
| `builtin:agent-maintainer` | Requester | `files.read`, `files.edit`, and `files.push` on owner-exposed, qualified skills and MCP mounts |
| `builtin:agent-operator` | Maintainer | `agent.prompt.direct`, `agent.command.invoke`, and `agent.interrupt` on `agent` |

Resolve the built-in ladder in the catalog. Explicit assignments remain additive with custom roles and direct grants. Raw terminal input, non-ready admission, native session or model selection, private history, usage, artifacts, and owner-file attachments are separate from the four delegated tiers. A newly installed provider cannot confer maintainer access unless Bob exposes it for common-plugin maintenance. Each admitted request still uses the canonical resource identifier. A stored role instantiated from a template remains fixed to its chosen resource.

### Resolve the Default Group Without Enrollment

Store `default_permission_group` in the retained target policy. New policies and older policies without the field use `agent-requester`. The value accepts any of the six canonical built-in names. Pin the selected catalog revision along with it. On a keyed target, a current roster admin and the verified managed-self runtime retain their system memberships. For other verified callers, a retained assignment to any of the four `builtin:` peer groups replaces the default. An expired peer group assignment continues to suppress fallback until the last such assignment is removed.

Add the active permissions from owner-defined roles, template-created roles, and direct grants to the applicable group. For example, `skill-reviewer` gives Alice access to review one mount while Bob's requester default continues to authorize her verified mail and work requests. Bob can explicitly assign `builtin:agent-observer` to restrict those contact rights while keeping her review access. `access list` and `access explain` report which source supplies each effect. See [the role composition decision](explore/adrs/0003-add-scoped-roles-to-applicable-group.md).

Apply the default without enrollment. A new peer may use verified identity evidence the ingress can substantiate or use the unsigned lane where the operation allows it. The default sets the access floor on eligible unsigned routes. For example, Alice's observer assignment denies her verified work request. A separate unsigned request can use Bob's `agent-requester` default and arrives labeled anonymous. The same rule applies when Alice's retained assignment has expired. See [the anonymous access decision](explore/adrs/0001-default-group-sets-anonymous-access-floor.md).

Reject invalid supplied proof and end a refused signed submission without an unsigned retry. Use verified identity or anonymous provenance for attribution. A name supplied by the caller carries no identity authority. Mail still needs its transport's sender evidence and uses the verified identity's applicable group and additive permissions. Disabling public prompt input controls the separate public endpoints. It leaves requester-default admission available on the regular work-request route.

Derive permissions from the selected group without changing the proof. `managed-self` as a default provides that group's non-admin policy effects for Bob's resources, while membership and signatures still identify the actual caller. `agent-admin` as a default gives otherwise-unassigned callers admin-exclusive permissions, including the permission to change the default. Keep operation-specific checks such as qualified roster-key proof and the first-key enrollment ceremony. They govern the roster independently of the fallback setting.

### Change the Default Without a Running Agent

Expose `PUT /v1/admin/default-permission-group` with `schema_version: 1` and the selected name. Use the same request model and `admin.default-group.set` effect on `policy` for the direct passive route `PUT /houmao/agents/{agent_ref}/admin/default-permission-group`. The passive server resolves the retained owner domain and verifies its own request-bound caller proof where supplied. It updates the policy directly when it serves that owner domain. Both routes use the same authorization and update transaction. See [the stopped-agent decision](explore/adrs/0004-change-default-without-a-running-agent.md).

`agents single ... access default-group set <group>` supports the verified gateway, an explicitly selected verified passive endpoint, and `--retained` for an explicit owner-local call. The local call verifies the retained owner and authenticates the selected caller in process. Use the existing SSH proof mechanism for a selected key and the applicable rules for unsigned admission. Execution ownership permits opening the store. The mutation still requires current effective `agent-admin` authority. Choose the path before submission and treat a refusal or uncertain result as the outcome of that attempt.

Resolve stopped or detached targets from verified retained owner records. Verify the selected target and original admin basis in the same owner transaction that writes the default and audit record. Preserve the roster and open epoch. Fail closed when the retained policy is missing, inaccessible, ambiguous, or replaced during selection. Track the setting revision independently of its catalog revision. Recheck that revision and group eligibility before queued handoff, protected disclosure, or incoming mail deposit. A setter on any path retires earlier fallback decisions even if a later setting restores the original value.

### Classify Effects for Managed Self and Administration

Classify each supported client-facing effect as non-admin or admin-exclusive in the host catalog. `managed-self` gets every supported non-admin effect on its verified current runtime and resources. It does not need an extra self-only mount opt-in. Owner exposure of a backend capability and operation-specific checks still apply to every caller. Agent-admin includes administrative effects such as admin roster changes. New effects need an explicit classification before they qualify for managed-self. Custom roles and templates cannot supply admin-exclusive effects. Direct local policy editing, OS execution authority, and passive backing trust keep their existing admission mechanisms.

### Enforce Incoming Mail at Bob's Delivery Boundary

Authorize `agent.mail.deliver` on the recipient's retained domain using the current recipient binding. Match verified membership from Bob's trusted offline registry or a provider-authenticated account to a unique explicit principal when one is known. Resolve the sender's applicable group and additive permissions under Bob's keyed policy. A sender needs no enrollment at Bob to use the default. Preserve validated transport issuer and sender evidence. Treat message headers, display names, and user-supplied IDs as content.

The receiving transport must obtain a current recipient-policy decision before mailbox publication or notifier visibility. Read retained policy locally under the recipient authority where available. A remote registry or provider uses a deployment-authenticated delivery verifier for Bob's retained policy. Scope that verifier to delivery and recipient authority. It stays available when Bob stops or detaches the gateway. Preserve the transport's recipient semantics when evaluating every addressed delivery, including replies and copy recipients. Denial or unavailable authority produces a delivery refusal and never a confirmed recipient receipt.

Integrate the check at the offline mailbox delivery transaction, where the registry and local adapter resolve final recipient registrations. A daemon-free local path can qualify when the protected store has a trusted writer and the recipient policy is available there. Test provider-backed ingress through SMTP, JMAP submission, and other enabled deposit paths. Resolve final recipient bindings after aliases or routing changes. Treat a provider submission receipt separately from a confirmed delivery. A deployment must refuse or disable a keyed binding if any route to that inbox cannot enforce the check. An initialized empty roster keeps open-admin delivery subject to the transport's existing authentication and delivery rules. A keyed recipient needs an admitted sender before delivery. Missing policy produces a refusal.

Alice-to-Bob mail uses Alice's sender binding. Bob's `mailbox-sender` template delegates use of Bob's own mailbox and is a separate grant. Authorizing delivery does not authorize a gateway prompt. The notifier retains its existing owner-controlled wakeup and rendering rules for mail that was admitted.

### Use Qualified Update Providers for Both Common Plugin Types

Continue using the versioned file API for skills. Generalize discovery and dispatch from one implied mount to multiple exact resource IDs and add a typed MCP declaration mount on the qualified DSH Web adapter. Bob's owner enables each provider and its scope. Each mount keeps its own draft lease, published base, and candidate attribution. Native maintenance still coordinates publication across resources that share an activation boundary. Successful publication returns separate evidence of publication, activation, and readiness. Backend capability discovery identifies supported types. An unavailable MCP provider produces an explicit unsupported result.

Stage only MCP declarations that the native adapter can validate and activate independently. Let maintainers add, replace, or remove entries using owner-approved connector references and permitted configuration fields. Keep executable launch specifications, raw credentials, and unrestricted network destinations in owner-controlled connector setup. This prevents publication from introducing independent process or control effects under the maintenance role. Validate both when saving a candidate and before handoff. A host-wide native MCP manager qualifies only when its affected scope is owned by the selected agent. Require that confinement or refuse publication on a shared host. Activation reconciles the selected MCP scope under the existing idle boundary and preserves the agent and conversation. Skills and MCP updates stay separate from harness packages and gateway plugin instances.

### Materialize Resource Templates Into Exact Roles

Extend `access role-put <role>` to accept `--template <template> --resource <canonical-resource>` alongside the existing exact-permission form as a mutually exclusive input. The owner can then call `access role-assign <principal> <role>` with the normal optional expiry. `access list` exposes the built-in catalog, available templates, and effective assignments. `access explain` identifies the definition or template revision, exact held effects, and current or unresolved resource availability. Store the exact rows and template provenance. Adding a capability later leaves previous assignments at their captured scope.

| Template | Resource | Effects |
| --- | --- | --- |
| `skill-reviewer` | One `files:<mount-id>` | `files.read` |
| `skill-editor` | Same | `files.read`, `files.edit` |
| `skill-publisher` | Same | `files.read`, `files.push` |
| `skill-maintainer` | Same | `files.read`, `files.edit`, `files.push` |
| `mailbox-reader` | One `mailbox:<channel>:<digest>` | `mail.list`, `mail.peek` |
| `mailbox-sender` | Same | `mail.send` using that mailbox's sender identity |
| `ag-ui-viewer` | One `ag-ui:thread:<digest>` | `ag-ui.output.read` |
| `ag-ui-runner` | Same | `ag-ui.output.read`, `ag-ui.input.submit` |
| `plugin-actions` | One `plugin:<instance>:<binding-id>` | Explicit repeated `--action` selections from the instance's declared actions |

An AG-UI client that needs capability discovery can receive the separate `ag-ui.capabilities.read` grant on `ag-ui`. A plugin-specific role such as a CCCC chat sender is an instance of `plugin-actions`. The existing plugin action declaration supplies the vocabulary. Verify the selected action set against the live or trusted retained instance declaration. If the declaration is unavailable, report it and leave the role unchanged. Exact ordinary grants remain available from the owner context while detached. Report live applicability as unresolved when the binding or installed capabilities cannot be verified. Admission always checks the actual active resource before use.

### Store Managed-Self Keys in Owner-Private SQLite

Resolve the Houmao configuration root in the verified execution owner's context, normally `~/.config/houmao`. Launch, join, gateway, passive ingress, and CLI use that same retained root even when a tool runs with a different home environment. Reuse `gateway-access/<scope>/authorization.sqlite3`, where the owner scope identifies the execution context and logical agent. Add a private credential table keyed by generation and key ID. Keep public registrations in the policy records used for verification. Use the existing checked owner-private directory and database handling for SQLite state and journals. Keep private material out of policy snapshots, audit and inspection output, manifests, registry records, and environment variables. Exclude the database and its sidecars from remotely selectable file exports, including owner-file mail attachments.

When the owner reserves a generation, generate a fresh Ed25519 key and commit its private record and matching public registration in one SQLite writer transaction using the store's existing `synchronous=FULL` setting. Verify that the stored key matches the public registration before startup uses it. This runs before native process startup or gateway attach for a new launch. A supported join provisions after verifying the adopted session's owner and before publishing its managed generation. The public registration identifies at most one active key and includes its revision. Prepared credentials become usable for self proof when the generation is verified live and current.

The launch profile provisions the key automatically, including when it starts the agent alone. A combined launch requires the same current registration before it publishes gateway readiness or reports success. Both foreground and background attach use existing native and listener startup requirements. If validation fails after the agent starts, use the existing structured auto-attach failure with the session identity or manifest reference. Keep the started agent running and clean up gateway resources created by that failed attach. Registration is independent of the roster and open admission.

Self commands select the key from the owner-private database through the verified owner, current generation, and active registration. Environment variables can locate runtime records. Use the selected key only to sign validated SSHSIG challenges bound to the target, generation, listener, request bytes, and registration revision. Gateway and passive verification read the public binding. Headless turn workers, recovered processes in the same verified generation, and subsequent gateway attachments reuse the committed registration. A new generation receives a fresh key and old-generation proof ceases to authorize effects.

Rotation and revocation require current effective `agent-admin` authority or proof from the currently registered key. Verify possession of the candidate and its binding to the same runtime before replacement. Use the owner policy transaction to recheck authority, generation, and expected registration revision and commit the private record and active registration together. An interruption before commit preserves the previous key and registration. After commit, reopening the database resolves the new pair together. Recheck the revision during proof admission and protected handoff. Revocation retains registration history. Startup or reconciliation may retry an initial write that never committed. A missing or invalid committed credential requires authorized recovery. An unavailable database fails closed and requires recovery of the retained store.

Linux-account file permissions provide isolation between owners. Agents sharing a UID share that UID's access to credentials and policy. Separate Linux accounts provide cross-agent filesystem isolation. Keep operator-admin private keys in the operator's own account for that separation. `agents self files` and `agents self refresh` select the current self key. `agents single ... files --self-signer` continues to select the source's stable peer key for explicitly signed peer calls. Admin signing and passive backing authority keep their separate selections.

Include qualified native observation, refresh, and file operations when their declared effects are non-admin. Ordinary edits within a mount cannot alter its authorization metadata. An explicitly selected unsigned operation still follows the target's open or default admission rules. Reject fingerprints that would confuse self and enrolled peer or admin identity. A `managed-self` default supplies applicable permissions while proof of the registered identity still requires the bound key.

### Classify Work Requests and Direct Input Before Admission

Add `submit_work_request` to `/v1/requests`, with `agent.request.submit` and a bounded text payload. At handoff the gateway creates trusted attribution from verified caller proof or labels unsigned input anonymous under the applicable default or open policy. Render the supplied text as quoted request data. Bob's instructions govern how to act. Keep sender text out of execution metadata and native command classification. Work requests use the current conversation, configured model, and ready-only handoff. The scoped request command keeps target verification and supports signed or unsigned input without recipient enrollment. Select the unsigned lane before submission. A signed refusal ends the attempt. Return existing request and handoff evidence.

Map existing verbatim `submit_prompt` and `/v1/control/prompt` to `agent.prompt.direct`. Check `agent.command.invoke` before dispatch whenever a supported slash command can execute, including command-like text on a direct prompt route. Use one classifier across direct ingress and queued handoff so slash text cannot fall through to unreviewed native or raw input. Start with the maintained qualified controls such as `/compact`, `/clear`, and `/new` where supported. Require the existing model, native session, and admission effects when a command would exercise them. Keep unsupported or ambiguous command handling as a typed refusal. Interruption retains `agent.interrupt`. Unrestricted raw keys retain `agent.input.raw` under their current authority. The typed distinction applies independently of queue timing.

Use the same semantic operation selector for passive proxy ingress and direct headless/passive execution paths. Authorize the resolved body at the original ingress and recheck it at handoff. Preserve caller proof and permission scope on the existing owner-local relay. Existing direct prompt and turn entries require direct effects even without an attached gateway.

Keep the attached gateway's work-request queue available through the gateway and its passive proxy. Add `POST /houmao/agents/{agent_ref}/work-requests` to the passive server for direct delivery to a verified running target with a detached gateway. Select the gateway or direct passive path before signing and submission. The direct route accepts only `submit_work_request` with bounded text and checks `agent.request.submit` against the same retained policy. It preserves verified or anonymous attribution and uses the same renderer. The current conversation, configured model, and ready-only handoff apply on either path. See [the detached work-request decision](explore/adrs/0005-deliver-detached-work-requests-through-passive-server.md).

Start with the owner dispatch and readiness machinery for passive-managed DSH Headless. Require a verified owner route for each advertised native backend. Acquire ready-only owner admission, then recheck the original caller basis, current generation, and detached selection before native effects. Hold the readiness claim through handoff. The direct passive path handles one immediate handoff. Busy or uncertain readiness, stopped targets, and unqualified native paths return explicit results. If attachment or authority changes before handoff, settle the original attempt before native effects. The receipt identifies the request and distinguishes admission, confirmed handoff, and uncertainty. Private turn output retains separate permissions. Ordinary mail remains an explicit contact operation under recipient policy.

For AG-UI, feed its structured task context through the attributed request renderer. Exact thread input and output rights authorize the run. Use an internal admission object for any separately approved AG-UI session or model options, since the public work-request payload accepts text alone. Keep connection, destination, and event-publish permissions separate. The existing direct gateway surfaces carry verbatim and native control input.

Reuse typed admission for composed operations such as gateway prompt reminders. Keep generated mail and plugin wakeups under their own declared operations. The application preserves these distinctions even when multiple surfaces run under Bob's OS account.

### Retain Candidate and Readiness Boundaries

A draft write and commit remain `files.edit` effects. A publish remains a `files.push` effect on the exact mount. A signed draft retains its actor identity across the open-to-keyed transition. An anonymous draft capability binds to the open epoch or default revision that admitted it. A fresh request must have current rights. Any pending handoff admitted under an old open epoch or replaced default is fenced. The author and publisher remain independently attributable.

Self may draft during a turn. An immediate publish or live native refresh that needs maintenance returns `busy` when the target is doing work. For an explicit deferred publication, `agents self files push --when-idle` selects the saved candidate, its expected base, and an operation ID. The gateway requires current managed-self proof and `files.push` on the exact mount. It retains the admitted intent and returns a receipt that can be checked with `files status <operation-id>`. See [the self-publication decision](explore/adrs/0002-schedule-self-publication-at-idle.md).

The gateway waits until it can acquire the existing owner and native maintenance boundary. An active, pending, or uncertain native turn can delay acquisition. A transient `busy` result before handoff keeps the scheduled intent pending. Recheck the original authorization, managed-self registration revision, target generation, listener, mount qualification, candidate, and base at handoff. A stale target, lost authority, or moved base settles the intent before publication and leaves the candidate saved. A same-generation key rotation or listener replacement permits a fresh authorized request with a new operation ID. It retires the earlier pending authority.

Bind the timing mode to the retained operation ID. Record an intent waiting for idle separately from an interrupted attempt. A repeated submission with the same publisher and exact intent returns the current receipt. Dispatch commits at most one publication handoff and reconciles interruption through existing publication and activation evidence. `files status` reads that evidence without initiating work. Same-home versioned history follows the existing mount rules. Native installations and relaunch use their existing workflows.

## Risks / Trade-offs

- **Same-account access** → Resolve each credential from its verified owner and scope. The Linux UID is the filesystem trust boundary. Keep the database and its sidecars outside remote file-export paths.
- **Gateway startup and crash recovery** → Commit the private record and public binding together when reserving a generation. Use the committed key through worker and listener restarts. Refuse unavailable or inconsistent retained state and preserve the registration history needed for recovery.
- **Privilege changes on upgrade** → Keep exact old grants visible, retire the ambiguous prompt action, and pin ordinary built-ins and template rows. Advance protected proofs and handoff checks only under the current policy.
- **Disagreement between text parsing and native command handling** → Exercise every maintained ingress with command-shaped inputs. Require qualified backend handling before advertising a direct native command.
- **Busy self-update** → Let the current managed runtime schedule a saved candidate. Keep waiting and handoff distinct in the receipt, and recheck the original authority and base when maintenance becomes available.
- **Multiple incoming mail paths** → Verify sender and recipient authorization before durable delivery on every path to a protected binding. Test provider and local submission as well as the normal shared registry route.
- **MCP declarations may launch work** → Publish only the typed, owner-approved connector surface. Preserve distinct native effect, activation, and readiness evidence.
- **Anonymous authority** → Show the access floor when inspecting or changing the default. Narrowing an explicit assignment only narrows requests under that verified identity. Selecting `agent-admin` gives otherwise-unassigned callers admin-exclusive policy effects.

## Migration Plan

1. Preserve retained admin and peer enrollments and owner-defined policy. Initialize the requester default for older policies without the field. Show it in catalog inspection and document how to select another group. Keep legacy `agent.prompt` rows inspectable with a retired-action diagnosis.
2. Qualify all delivery paths for each keyed mailbox, record the transport-to-principal bindings, and assign ingress permissions before lowering access to the observer level. Disable protected delivery where verification is unavailable and document how to restore a qualified binding.
3. Switch every affected client to the explicit request or direct effect. Drain or refuse pending prompt approvals that lack current exact effect evidence. Replace broad prompt grants with the chosen built-in role or exact permission set.
4. Upgrade the retained authorization schema to include the managed-self credential table. Preserve owner policy and stable peer and admin enrollments. Relaunch agents with older self credentials to provision a fresh generation in SQLite. Recover an unavailable database through the retained store recovery procedure before trying to provision or change keys.
