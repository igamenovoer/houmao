# Tasks

## 1. Pin and Qualify the Native Integration Seams

- [x] 1.1 Add development-only source/runtime preparation under `tools/dsh/` for upstream `39163dd30f703a79079e2d2446545cff3c453738`; verify the ignored checkout, executable version/build, and repeatable setup commands without modifying an existing personal DSH home.
- [x] 1.2 Qualify packaged companion-module loading, literal system-prompt sections, native inbox admission/claim evidence, pre-activation pending-input reconciliation, and uncompressed journal headers against the pinned runtime with a controlled model; record the observed contracts and corresponding conformance tests.
- [x] 1.3 Publish the headless compatibility/setup reference and an acceptance map for every delta scenario; verify source/build identity, unsupported operations, and live-versus-hermetic evidence are explicit.

## 2. Add Isolated Tool Configuration and Native Prompts

- [x] 2.1 Add the canonical DSH setup parser, starter/fixture tool adapters, and explicit native-DeepSeek-Messages and generic compatible-route configurations; verify protocol mismatch, absent model metadata, invalid routes, and secret-free provenance with unit tests.
- [x] 2.2 Extend maintained project, credential, model/reasoning mapping, backend, launch-override, and schema selectors for `dsh`/`dsh_acp`; verify supported headless resolution and explicit rejection of unsupported backend/mode/native-login combinations.
- [x] 2.3 Generate private DSH/shared-agent roots, profile, uncompressed persistence, selected skills/MCP entries, and no-question startup policy; verify two-agent isolation, conflicting ambient auth, explicit capacities, and startup-only HMR behavior.
- [x] 2.4 Package the DSH native prompt and admission companion under product assets; verify literal braces/multiline prompts, built-in guidance preservation, empty-role cleanup, wheel resource availability, and no chat-bootstrap fallback.
- [x] 2.5 Document DSH setup fields, endpoint conventions, permissions, and native prompt/skill projection; verify examples resolve through maintained project/profile preparation with synthetic credentials.

## 3. Implement ACP Transport and Turn Lifecycle

- [x] 3.1 Implement the driver reader/writer, request correlation, concurrent stderr draining, capability validation, and supported permission responses; verify interleaved notifications/server requests, malformed stdout, wrong-session updates, pipe pressure, and early EOF with controlled subprocess tests.
- [x] 3.2 Implement create/exact-resume/model selection/prompt/close through the managed headless envelope; verify two prompts across separate processes retain one native conversation and missing, incompatible, occupied, or wrong-workspace resume never creates a replacement.
- [x] 3.3 Capture raw ACP frames separately from canonical events and rendered console output; verify result/limit/error mappings and provider-debug artifacts through runner and passive-server event tests.
- [x] 3.4 Implement native handoff evidence, session invocation locking, process-birth fencing, and pending-attempt persistence; verify helper launch is insufficient proof, independently resumed controllers cannot overlap, and controller timeout does not finalize live execution.
- [x] 3.5 Implement native cancellation, bounded process-tree cleanup, and explicit abandoned-input reconciliation before resume; verify graceful cancellation, hung cancellation, abrupt death before/after inbox claim, persistence failure, and no automatic prompt replay.
- [x] 3.6 Document lifecycle, timeout, interruption, resume/reset, and unsupported-operation behavior; verify the guide distinguishes Houmao acceptance, native handoff, native outcome, and managed cleanup failure.

## 4. Add Native Usage Collection

- [x] 4.1 Add a version-qualified DSH raw-journal reader and bound-source discovery; verify header/session ownership, format selection, partial tails, truncation/replacement, and nonchargeable resume baselines with sanitized fixtures.
- [x] 4.2 Normalize settled message/attempt samples and retry boundaries into existing observations; verify disjoint cache buckets, absent versus zero, reasoning overlap, exact/derived totals, conflicting samples, failed attempts, and ignored ACP occupancy.
- [x] 4.3 Associate a managed interval with its proven native root-turn set and explicit descendant scopes; verify child-triggered continuation, inherited-history exclusion, unknown inclusion, and no managed/native double finalization.
- [x] 4.4 Integrate immutable finalization, recorder-outage recovery, original generation/cutoff retention, and incremental cursors; verify concurrent reconciliation inserts each terminal record once and keeps public evidence free of content and secrets.
- [x] 4.5 Update usage reference documentation and the acceptance map with DSH source/scope rules; verify every accounting example identifies availability and provenance correctly.

## 5. Wire Gateway and Passive-Server Authority

- [x] 5.1 Add the DSH headless gateway execution and immediate-dispatch path; verify attach between turns, busy/unavailable refusal, expiry before handoff, generation replacement, and provider death without delayed dispatch or resend.
- [x] 5.2 Extend passive-server headless launch, authority restore, prompt/interrupt/stop, events, raw artifacts, and usage routes; verify restart rebuilds control or reconciles terminal evidence without replaying active attempts.
- [x] 5.3 Extend the stale-controller manifest regression to DSH and verify status/capability/gateway lifecycle operations preserve newer native session and turn state.
- [x] 5.4 Verify existing mailbox reminders and owner-bound plugin/CCCC dispatch against a controlled DSH agent; assert periodic reminders, transport selection, ownership, and no-buffer ordinary delivery remain intact, and document the supported integration paths.

## 6. Extend Local Fixture Workflows

- [x] 6.1 Extend the current fixture helper and descriptors for DSH raw ACP, manager, and passive-server headless lanes; verify equivalent resolved model/protocol/auth inputs, external private roots, unattended defaults, and synthetic-account CI.
- [x] 6.2 Extend `skillset/dev/houmao-dev-launch-agents/` and fixture/setup docs with DSH preparation and launch instructions; verify a fresh-host cloud configuration requires no local model or auth JSON and never prints or tracks key values.
- [x] 6.3 Add opt-in live qualification under `scripts/qualification/dsh/` for DeepSeek prompt/tool/complete, interruption, exact resume, usage, and two isolated homes; run it and record actual build/model/protocol evidence, with explicit not-run reasons for any unavailable self-hosted lane.

## 7. Complete Cross-System Acceptance

- [x] 7.1 Run focused unit/integration suites and required `pixi run format`, `pixi run lint`, `pixi run typecheck`, and `pixi run test`; verify DSH scenarios pass and existing Claude/Codex/Kimi regressions remain green.
- [x] 7.2 Run distribution build/metadata checks, strict docs build, scenario-evidence and secret audits, and OpenSpec validation; verify product assets ship while credentials, reference checkouts, and private runtime state do not.
- [x] 7.3 Finish the headless acceptance report with remaining limits and update implementation-time roadmap references to both ordered changes; verify headless delivery is recorded without closing the combined #74 scope before change 02 passes.

## Workflow Follow-up

- Review, validate, synchronize, and archive change 01 through the corresponding OpenSpec workflows after implementation acceptance.
- Apply `dsh-02-add-interactive-web-backend` only after change 01 is implemented, validated, and synchronized; preserve the first change's qualified source and runtime contracts.
