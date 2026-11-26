# Design

## Context

The runtime starts native resources before it publishes authority. The manager also reuses its Click launch implementation for owner stdio, including option validation and completion rendering. The refactor gives startup, request validation, and rendering clear ownership while correcting the observed state inconsistencies. [Proposal](proposal.md)

## Goals / Non-Goals

Use the existing CLI, HTTP, stdio v1, runtime manifests, and SQLite layout as the compatibility baseline. Keep process cleanup tied to the exact attempt and owner. Treat the managed run-mode matrix, optional gateway auto-attach, native replay and continuation, and existing authorization boundaries as design constraints.

The companion adoption retirement owns the change to supported launch origins. Keep relocation of public passive DTOs and retirement of the remaining standalone server internals outside this client extraction. [Adoption Retirement](../retire-manual-agent-adoption/proposal.md)

## Decisions

### Give Required Startup One Commit Point

Keep preflight ahead of effects. In `start_runtime_session`, record the rollback actions for the hook observer, newly owned backend resources, and partial generation publication as each step acquires them. Startup commits after the manifest and required authority publication succeed. Register each action with the exact execution binding and generation so cleanup can also run if controller construction fails.

Use birth-specific backend teardown where ordinary stop preserves a tmux session or native state. Scope cleanup to resources created by this attempt. If publication partly succeeds, withdraw only the corresponding generation, retaining preexisting homes, work directories, mailbox data, and authorization history. Preserve existing best-effort writes and optional gateway auto-attach semantics. Returning cleanup responsibility to the caller would still leave gaps before a controller is returned. [Runtime Startup](../../../src/houmao/agents/realm_controller/runtime.py#L2605)

Withdraw partial registry and gateway publication while the manifest can still verify the generation, or use an equivalent owner-fenced operation. Release the remaining session artifacts after that verification. A competing generation keeps its publication.

### Return Launch Completion to Both Adapters

Extract the shared project-launch operation behind a typed request and typed completion. Pass the explicit project context and reuse existing profile resolution, launch preparation, and `LocalManagedAgentLaunchResult`. Build the receipt from the verified launch and manifest facts. Click renders the receipt and owns terminal handoff. Owner stdio serializes the same facts into the existing v1 result, including the top-level identity, mode, backend, and verified Web surface used by locator publication.

Keep target-only paths and environment resolution inside the owner context. Preserve existing CLI parsing and output data across plain, fancy, and JSON modes. Capturing rendered output makes the owner result depend on incidental CLI changes after the runtime has already started. [Owner Launch](../../../src/houmao/execution/application.py#L75) · [Locator Publication](../../../src/houmao/execution/router.py#L134)

The local renderer currently exits with status 2 after reporting an optional gateway attach failure. In owner stdio that exit can escape before the v1 response is written. Carry the existing `gateway_auto_attach_error` field in a completed owner response. The operator CLI can then publish the locator, emit the partial result, and exit with status 2. Keep the existing separate recovery outcome if locator publication fails. [Local Completion](../../../src/houmao/srv_ctrl/commands/agents/core.py#L1380)

### Validate Each Owner Operation Once Before Setup

Parse v1 arguments into operation-specific validated values and classify read-only status in the same finite operation definition. Admission and dispatch use that result and preserve the established argument names, defaults, repeatable values, and rejection diagnostics. Validate admitted project scope and route identity before setup and recheck the exact saved binding and generation at the operation boundary. Read-only requests, including cleanup dry runs, use the same classification for both initialization and execution scope.

Keep OS authorization, the fixed stdio entrypoint, request correlation, deadlines, and post-admission uncertainty at their existing boundaries. Two independent validation tables have already required synchronized changes for gateway attach fields and read-only controls. [Owner Admission](../../../src/houmao/execution/owner.py#L360) · [Execution Contract](../../../openspec/specs/agent-execution-contexts/spec.md)

### Centralize Shared Backend Capability Facts

Start with the existing `BackendKind` and run-mode definitions. Give the four sites that validate or forward gateway tracking timings one authoritative capability query. Keep explicit backend selection, adapter construction, and persisted identifiers at their existing boundaries. Compare the complete current matrix, including Web and Hermes TUI refusal and existing direct-attach acceptance for service and headless modes. Keep actual tracker eligibility distinct from the ability to accept a timing value. Inferring both from run mode would misclassify structured Hermes TUI and alter current direct attach behavior. [Run Modes](../../../src/houmao/agents/realm_controller/run_modes.py) · [Attach Validation](../../../src/houmao/agents/realm_controller/runtime.py#L5430)

Keep the manager launch, direct runtime start, and gateway attach policies distinct. In the current code the manager rejects timing values on nonterminal launch surfaces, direct start permits headless timings with auto-attach, and direct service or headless attach can accept timing values. Check omitted values separately from explicit overrides.

### Update Mailbox-Local State and Summaries Together

Put the local message mutation and summary refresh behind one mailbox-local operation. Call it from filesystem move and archive and ordinary mark. Recompute from message rows inside the same local transaction, including on a retry with the same destination. Preserve checks for recipient ownership, answered and other independent flags, deterministic locks, projection placement, and the shared-index commit ordering.

Keep the existing local SQLite schema. Refresh an already-stale summary when the thread is touched or through an existing summary rebuild that preserves message rows. A full mailbox repair can reconstruct recipient-local flags, which makes it unsuitable for routine correction of a derived count. [Archive Write](../../../src/houmao/mailbox/services.py#L1048) · [Mark Write](../../../src/houmao/mailbox/managed.py#L2009)

### Share Qualification and Parsing After Target Resolution

After manual adoption is retired, use the verified launch version and the maintained detector registry for parser-backed TUIs. Share the qualification result and version-aware parser invocation across the local manager and gateway observer, passive observer, and retained server poll where it still runs. Keep pane resolution, exact socket and generation checks, hook handling, history, and observation scheduling with each caller. Preserve native observation for Hermes TUI and Web.

Expose the existing unsupported-version diagnostic for missing, unparseable, or below-floor evidence. Resolve the supported detector before parsing and pass its selected version through to the parser. Sharing only capture or parser utilities would leave the observed qualification drift in place. [Shared Observer](../../../src/houmao/shared_tui_tracking/ownership.py#L358) · [Passive Observer](../../../src/houmao/passive_server/observation.py#L170)

Keep the registry's actual compatibility intervals, configured fallback, and opt-in experimental selection. A profile's qualified-through version documents evidence and does not become an upper bound for an open-ended registration. The retained server poll still accepts its existing registration and manifest version sources.

### Validate Durable Hermes Receipts at One Boundary

Reuse the full saved Hermes TUI receipt model and one identity check for owner recovery and the backend reader. Retain daemon replay and native RPC in the backend. A valid terminal receipt can settle the matching attempt, a queued receipt preserves the admission, and incomplete evidence leaves recovery unresolved until valid evidence or an authorized lifecycle transition. The receipt writer already emits the full schema. Independent subset checks let malformed evidence settle an attempt prematurely. [Receipt Writer](../../../src/houmao/agents/realm_controller/backends/hermes_tui.py#L484) · [Owner Reconciliation](../../../src/houmao/agents/realm_controller/owner_admission.py#L822)

### Compose the Passive Client From Shared HTTP Transport

Give the factory and passive client a shared HTTP transport with explicit passive operations. Keep existing constructor inputs, supported operation signatures, typed DTOs, timeouts, permission proof and signing inputs, and raw artifact handling. Move any maintained operation currently inherited through the old server client onto the passive implementation as part of removing that inheritance. The old client expects a different health payload, and its inheritance exposes unrelated CAO methods to current consumers. [Passive Client](../../../src/houmao/passive_server/client.py#L171) · [Client Contract](../../../openspec/specs/passive-server-client-compatibility/spec.md)

## Risks / Trade-offs

- A publication failure can occur after some discovery state becomes visible. Exercise the exact rollback owner and generation at both the manifest-write and required-publication boundaries.
- A v1 peer or CLI consumer can depend on an existing result field or failure outcome. Compare envelopes and CLI receipts using the same admitted inputs, including a valid Web result and an indeterminate owner response.
- Gateway timing input policy differs from parser support. Pin both gateway execution modes and direct attach behavior in the current capability matrix.
- Local mailbox state and shared projection state span separate stores. Preserve the existing cross-store failure handling and test a retry to an already projected archive destination.
- Passive proxying relies on exact signed request components. Use pair, auth, and raw text artifact tests to exercise the extracted client. Preserve the signed transport's redirect, TLS, response bounds, and typed refusal behavior.

## Migration Plan

Apply as independently verifiable slices, starting with required startup cleanup. Land the adoption cutoff before consolidating shared TUI observation. Use the existing on-disk formats and protocol versions so individual slices can be reverted independently. Mailbox updates can repair derived counts from retained rows. Existing valid Hermes receipts remain readable.
