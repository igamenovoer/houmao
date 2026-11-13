# Tasks

## 1. Public SDK and Package Discovery

- [x] 1.1 Add the versioned public contracts under `src/houmao/gateway/plugins/` for definitions, strict configuration, owner/binding context, lifecycle, status, workers, events, dispatch results, and typed errors; verify public imports and strict typing without gateway implementation types in SDK signatures.
- [x] 1.2 Implement selected-only `houmao.gateway_plugins` entry-point resolution in the gateway environment; verify synthetic distribution tests for unselected import side effects, missing packages, duplicate advertised names, load failures, and unsupported SDK versions.
- [x] 1.3 Add deterministic binding-identity validation and the instance-factory boundary; verify repeated initialization preserves identity across process/package-version changes and factories cannot activate host-provided resources during route staging.
- [x] 1.4 Document SDK versioning, supported imports, package metadata, and the trusted-code contract in a gateway plugin authoring reference; verify every documented public symbol and entry-point example matches import/metadata contract tests.

## 2. Owner Configuration, Credentials, and Runtime Plumbing

- [x] 2.1 Add the dedicated versioned YAML/JSON configuration loader and public model, including instance IDs, optional explicit credential references, finite limits, whole-set replacement, and omitted-versus-empty selections; verify duplicate keys, unknown fields, malformed IDs, and invalid limits fail before persistence or process changes.
- [x] 2.2 Implement owner/binding-scoped state and selected private credential-file access; verify two-owner isolation, path containment, symlink/ownership/permission rejection, checkout exclusion, optional no-auth configuration, missing-file errors without ambient fallback, and same-source rotation without identity changes.
- [x] 2.3 Thread typed selections through `start_runtime_session()` and `RuntimeSessionController.attach_gateway()` and add `--plugins-config` to maintained scoped gateway attach commands; verify launch override validation and CLI/Python equivalence with deterministic runtime fixtures.
- [x] 2.4 Preserve selections across every `GatewayDesiredConfigV1` construction in capability publication and both gateway launch modes; verify refresh/restart continuity, explicit clearing, equivalent live reuse, and changed-live-config conflicts without mutating persisted or active values.
- [x] 2.5 Document installation into the actual gateway interpreter, private credential setup, launch/attach examples, gateway-only restart requirements, and configuration precedence; verify command help and examples against maintained CLI contract tests without using retired entrypoints.

## 3. Route Namespaces and Conflict Validation

- [x] 3.1 Add staged relative-router validation and host-owned prefixes/status reservations; verify invalid URLs, traversal, encoded separators, global middleware/lifecycle handlers, nested mounts, unsupported converters, and namespace escapes are rejected before resources activate.
- [x] 3.2 Implement effective-method and restricted-path overlap detection; verify equivalent parameter names, literal-versus-parameter overlap, terminal catch-alls, trailing-slash aliases, implicit methods, and disjoint-method coexistence with focused route-language tests.
- [x] 3.3 Validate the complete candidate inventory and reject every participating plugin instance before mounting survivors; verify registration-order permutations, core-route preservation, unrelated-instance availability, and zero credential/connection/worker activity for rejected instances.
- [x] 3.4 Add failed-instance custom-route guards and safe conflict diagnostics; verify host-owned status remains readable, custom requests return safe 503 responses, and authoring docs explain namespace ownership and the exact rejection policy with executable examples.

## 4. Lifecycle, Status, and Listener Policy

- [x] 4.1 Implement one lifecycle coordinator shared by service startup/shutdown and app-factory execution; verify production post-bind activation, resolved system-assigned ports, exactly-once lifecycle entry/exit in ASGI tests, and core readiness while plugin activation is pending.
- [x] 4.2 Implement per-instance asynchronous lifespans and supervised workers with cooperative deadlines and context revocation; verify partial-start cleanup, cancellation, unexpected worker termination, cleanup timeouts, in-flight request failure without cached resend, and failure isolation without service I/O under the execution lock.
- [x] 4.3 Add maintained plugin status snapshots, `GET /v1/plugins`, `GET /v1/plugins/{instance_id}/_status`, typed client reads, and private offline diagnostics; verify unknown-instance 404, safe failed-instance status, connection-state reporting, and status reads that make no plugin/service calls.
- [x] 4.4 Apply loopback policy before implementation import or resource activation; verify `0.0.0.0` reports disabled instances, denies custom routes and event intake, and never resolves credentials or starts plugin workers while retaining sanitized host status.
- [x] 4.5 Document lifecycle/connection state, reconnect reporting, cooperative cancellation limits, failure repair, and status/diagnostic fields; verify hostile exception/config/event/credential fixtures do not leak private material through default host diagnostics.

## 5. Immediate Event Dispatch and Sender-Owned Retries

- [x] 5.1 Add bounded immediate event dispatch using the existing ready-only admission seam and ordinary notification envelopes; verify busy headless/TUI targets, pending-input yes/unknown, active-hook gates, conflicting accepted work, oversized/invalid input, and command-looking content produce the specified immediate result without queueing.
- [x] 5.2 Add adapter/worker dispatch confirmation for local and managed headless execution and available TUI handoff evidence; verify thread creation and upstream queued acknowledgement cannot return success before actual handoff, with finite request deadlines and safe handling of launch failure.
- [x] 5.3 Capture and revalidate current execution incarnation during dispatch using existing generation/lifecycle evidence; verify body death before handoff, replacement under the same logical agent/session ID, and observed death after handoff but before response all fail the original request without forwarding to a replacement.
- [x] 5.4 Expose typed dispatch results/errors and HTTP mappings for retryable readiness/availability/body-loss failures versus permanent input/policy failures; verify HTTP 409/503/422, source-ID correlation, uncertain outcomes, absent-gateway connection failures, and success that means dispatch rather than completed agent processing.
- [x] 5.5 Fence and clean up unsuccessful in-flight attempts without retaining a notification payload; verify failure/timeout/shutdown leaves no late dispatch, gateway/body restart never resends an earlier message, and only a fresh sender request can retry successfully after readiness returns without adding queue schema, queued kinds, or receipt-ledger storage.
- [x] 5.6 Update plugin author/operator, protocol, admission, and system-file references for immediate failures and sender retention/retry ownership; verify examples propagate upstream failure and advance consumption only after confirmed dispatch, describe possible duplicates after lost responses, and match the unchanged existing queue/notifier semantics.

## 6. Independent Example and Installed-Package Qualification

- [x] 6.1 Add a standalone example distribution under `examples/gateway-plugin/` demonstrating public SDK imports, entry-point metadata, owner-bound routes, supervised resources, credential refresh or no-auth mode, immediate dispatch/error propagation, and shutdown; verify its own contract tests and complete install/configure/status instructions.
- [x] 6.2 Add synthetic independent distributions under `tests/fixtures/gateway-plugins/` and an offline wheel/environment qualification harness using temporary output roots; verify the harness cannot import Houmao or the plugin from the checkout and reports missing wheel/dependency prerequisites as explicit setup failures.
- [x] 6.3 Qualify built Houmao and external plugin wheels through actual detached and same-session gateway launches from outside the checkout; verify HTTP routes, selected-only discovery, owner/collision/failure isolation, immediate not-ready errors, body death/replacement during dispatch, no cached resend after recovery, explicit sender retry, operator access, and cleanup with deterministic stubs and no paid provider calls.
- [x] 6.4 Publish sanitized installed-package qualification evidence and example documentation; verify it records artifact versions, interpreter/environment facts, both process modes, results, and cleanup without keys, private paths, event bodies, or dependence on ignored checkouts/change-local launch scripts.

## 7. Final Integration Checks

- [x] 7.1 Run `pixi run format`, `pixi run lint`, `pixi run typecheck`, and `pixi run test`, plus targeted gateway/plugin/runtime integration suites; verify all required checks pass and existing core prompt, interrupt, reminder, notifier, usage, mailbox, and AG-UI contracts retain their behavior.
- [x] 7.2 Run strict documentation build, `pixi run build-dist`, and `pixi run check-dist`; verify the public SDK is present in the wheel, examples/tests/private artifacts are excluded, and documented plugin setup works against the built distribution.
- [x] 7.3 Run `openspec validate add-gateway-plugin-api --strict` and review acceptance coverage against issue #76; verify every spec scenario has test or qualification evidence and distinguish the delivered gateway SDK from deferred CCCC, remote-authentication, and general-SDK work.
