## Context

`houmao-server` already exposes the managed-agent API surface documented in [managed_agent_api.md](/data1/huangzhe/code/houmao/docs/reference/managed_agent_api.md), but the repository does not yet have one canonical live suite that validates basic end-to-end server behavior across both managed transports. The existing interactive demo path is workflow-shaped, depends on wrapper CLIs, and has already shown timeout, cleanup, and worktree-specific failure modes that are orthogonal to the server API contract itself.

The new suite needs to validate direct server-owned behavior for:

- starting a real `houmao-server`
- creating TUI-backed managed agents for Claude Code and Codex
- creating native headless managed agents for Claude and Codex
- reading managed-agent discovery and state through `/houmao/agents/*`
- submitting prompts through `POST /houmao/agents/{agent_ref}/requests`

Gateway lifecycle and gateway-mediated control are explicitly out of scope for this suite version. The suite should validate the direct server authority first, then leave gateway coverage to the existing gateway-focused tests and later suite expansion.

## Goals / Non-Goals

**Goals:**

- Provide one canonical live suite for basic `houmao-server` agent API verification across both TUI and headless transports.
- Exercise four real agent lanes: Claude TUI, Codex TUI, Claude headless, and Codex headless.
- Use only public server-facing HTTP routes for verification and prompt submission.
- Keep all run artifacts under one isolated per-run root with explicit logs, HTTP snapshots, and lane metadata.
- Make failures actionable by preserving launch, registration, prompt, and cleanup evidence rather than hiding them behind demo-specific orchestration.

**Non-Goals:**

- Gateway attach, gateway-mediated request routing, or mailbox follow-up coverage.
- Exact natural-language assertion of model replies.
- Replacing the existing demos or gateway-oriented integration tests.
- Making the suite a default CI requirement in the first version.
- Adding an opt-in pytest wrapper in this change.

## Decisions

### Decision: Make the canonical v1 suite a live operator-run suite under `tests/manual/`

The suite should be treated as a real-environment verification harness, not a default hermetic integration test. It depends on actual `claude` and `codex` executables plus valid local credential material, so the primary entrypoint should live under `tests/manual/` as an explicit operator-run suite.

Why this over `tests/integration/` first:

- it matches the repository’s existing split between hermetic integration coverage and manually executed real-tool checks
- it avoids misclassifying credentialed live-tool behavior as ordinary CI
- it still leaves room for a future opt-in pytest wrapper if the harness stabilizes enough

Alternative considered:

- Put the suite directly in `tests/integration/` with skip markers.
  Rejected for v1 because the live external-tool dependency is the primary behavior, not an occasional optional branch.

### Decision: Use a server-centric harness that talks to HTTP routes directly

The suite should start `houmao-server` as a subprocess, then use `HoumaoServerClient` plus direct CAO-compatible HTTP where needed. It should not drive `houmao-mgr` wrapper commands as its primary control surface.

Why this over demo-driven orchestration:

- the suite is meant to verify the API contract, not one demo workflow
- direct route usage isolates server/API failures from wrapper-shell behavior
- it avoids reusing the current brittle timeout and cleanup surface from the interactive demo pack

Alternative considered:

- Build on `scripts/demo/houmao-server-interactive-full-pipeline-demo/`.
  Rejected because that path is workflow-oriented and currently fails before it can serve as a stable API verification base.

### Decision: Gate every run on explicit preflight and server readiness checks

The suite should validate required executables and credential inputs before starting `houmao-server`, and it should not attempt any lane provisioning until `GET /health` succeeds on the suite-owned server.

Preflight for v1 should explicitly cover:

- `tmux`
- the selected provider executables (`claude` and/or `codex`)
- the selected lightweight fixture assets
- required credential material for the selected lanes
- Codex API-key-mode inputs when one Codex lane is selected

Why this decision:

- it turns the current implicit assumptions into operator-visible failures
- it follows the existing `HoumaoServerClient.health_extended()` control surface instead of adding a second readiness mechanism
- it avoids flake from racing server startup or silently missing `tmux`

### Decision: Treat TUI and headless provisioning as separate first-class flows

The suite should share one reporting and verification harness, but it should stage TUI-backed and headless agents through their native public lifecycle paths.

TUI lanes:

- install the tracked lightweight `server-api-smoke` profile for the selected provider
- create a CAO-compatible session through `/cao/sessions` with a configurable timeout budget whose initial default is 90 seconds
- materialize the delegated runtime artifacts under the suite-owned runtime root by calling `materialize_delegated_launch()`
- register the launched session through `POST /houmao/launches/register`

Headless lanes:

- build the native launch request from tracked fixtures by calling `materialize_headless_launch_request()`
- launch through `POST /houmao/agents/headless/launches`

Why this split:

- it matches the actual architecture: TUI agents become managed agents through creation plus registration, while headless agents use the native managed launch route
- it lets the suite verify the TUI registration seam explicitly
- it avoids forcing one transport into the other transport’s request shape

Alternative considered:

- create all four agents through `houmao-mgr` convenience commands
  Rejected because the suite would stop being API-centric and would inherit wrapper-specific failures.

### Decision: Use lightweight dedicated fixtures and copied dummy projects

The suite should introduce a lightweight `server-api-smoke` fixture family for roles, secret-free config inputs, and provider-specific recipes or blueprints, then use copied dummy-project workdirs per lane instead of repo worktrees.

For v1, the copied workdir should reuse `tests/fixtures/dummy-projects/mailbox-demo-python/`, but the agent role or blueprint should remain `server-api-smoke` rather than reusing the mailbox-demo role.

Why this over reusing heavyweight repo-scale fixtures:

- launch latency and prompt complexity stay bounded
- state transitions are easier to observe and less flaky
- cleanup is simpler because workdirs are suite-owned copies, not git worktrees

Alternative considered:

- reuse `gpu-kernel-coder` against the repository worktree.
  Rejected because the suite’s purpose is API contract verification, not repo-scale engineering behavior.

### Decision: Default suite artifacts under repo-local `tmp/` with an operator override

The suite should create its run roots under a repo-local default prefix such as `tmp/tests/houmao-server-agent-api-live-suite/`, while still allowing an explicit operator-provided output-root override.

Why:

- it matches the repository’s current generated-artifact convention
- it keeps live evidence easy to discover after failures
- it still lets operators relocate artifacts when needed for cleanup or disk management

### Decision: Use explicit stable lane identities and suite-owned cleanup state

Every lane should have an explicit stable lane id and explicit requested session or agent name. The suite should record:

- requested TUI session names
- returned terminal ids
- returned tracked agent ids
- manifest and session-root paths

Cleanup should use those explicit recorded identities rather than rediscovering from ambient state.

Why:

- it removes the auto-generated session-name cleanup hole that surfaced in the current demo
- it makes partial-failure cleanup deterministic
- it makes failure artifacts easier to inspect after the run
- it makes it straightforward to stop lanes first and then terminate the suite-owned `houmao-server` process while preserving both results

### Decision: Prompt verification should assert accepted admission plus observable state transition, not exact prose

The suite should submit one short prompt per lane through `POST /houmao/agents/{agent_ref}/requests` and verify:

- accepted request response
- non-`none` last-turn result or other clear post-request transition on `/state`
- for headless lanes, durable turn evidence when the accepted response includes `headless_turn_id`

Why this over asserting exact output text:

- API correctness is about admission, state progression, and inspectability
- exact reply text would make the suite fragile across model/runtime variation

## Risks / Trade-offs

- [Real tool launch latency exceeds default CAO client expectations] → Use suite-controlled direct clients with larger timeout budgets for TUI session creation and explicit bounded polling for prompt completion.
- [Credential or local executable drift makes runs fail before API verification begins] → Add preflight validation for required executables, credential env files, and selected fixture profiles before starting the server.
- [TUI registration adds complexity beyond plain `/cao/sessions`] → Keep registration as an explicit suite phase with recorded artifacts and separate failure reporting so creation and registration failures are distinguishable.
- [Live prompt completion remains provider-variant] → Verify accepted admission plus coarse state change rather than exact textual responses.
- [Cleanup after partial startup can still leak state] → Use explicit lane identities, suite-owned run roots, and best-effort stop plus tmux cleanup for known TUI session names during teardown.
- [Owned server shutdown order is ambiguous after partial failure] → Treat lane cleanup as the first shutdown phase and persist the final `houmao-server` process-termination result as separate run evidence.

## Migration Plan

1. Add the new `houmao-server-agent-api-live-suite` capability and suite-owned fixture family.
2. Implement the manual live harness and helpers under `tests/manual/`.
3. Stage isolated run roots and HTTP snapshot/report outputs under a suite-owned temporary root.
4. Document the required local executables, credential prerequisites, and supported invocation shape.
5. Keep all existing demos and gateway-oriented tests unchanged; this suite is additive.

Rollback is straightforward because the change is additive. If the harness proves too unstable, the suite files and fixtures can be removed without changing the public `houmao-server` API.

## Resolved Follow-Ons

- This change keeps the suite manual-only under `tests/manual/`; a future pytest wrapper remains a later follow-up if the live flow stabilizes.
- The first version should expose both one all-lanes aggregate mode and operator-selected per-lane execution from day one.
