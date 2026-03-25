## Context

The current direct `houmao-server` managed-agent API validation flow lives in `tests/manual/manual_houmao_server_agent_api_live_suite.py` and a sibling helper package under `tests/manual/houmao_server_agent_api_live_suite/`. That structure is good for a one-off manual harness, but it is a poor fit for the repository's current demo-pack pattern:

- it is not organized as a self-contained tutorial pack under `scripts/demo/`
- it does not expose a pack-local `run_demo.sh` stepwise workflow
- it does not expose a pack-local HTT/autotest runner with concrete case ids the way newer tutorial packs do
- it still carries test-oriented assumptions such as `tests/manual/` ownership and test-fixture naming

At the same time, the underlying pair and server contracts have shifted toward demo-owned native selector inputs and demo-owned run roots. The new pack needs to preserve the current direct server-API validation purpose while presenting it in the same runnable, inspectable, snapshot-verified format used by other maintained demos.

This change also needs a stronger testing contract than the old manual suite ever had. The first path worth driving end to end is not "run some manual helper and inspect its stdout"; it is one four-lane unattended direct API validation run that starts its own `houmao-server`, inspects state through public routes, sends real requests, verifies a sanitized report, and stops cleanly while preserving artifacts for later inspection. The demo pack and the HTT harness need to agree on that same canonical path.

## Goals / Non-Goals

**Goals:**

- Provide one canonical direct `houmao-server` managed-agent API validation pack under `scripts/demo/`.
- Expose one canonical non-interactive path, `run_demo.sh auto`, that runs `start -> inspect -> prompt -> verify -> stop` for the selected lanes without mid-run operator intervention.
- Preserve the existing four-lane coverage: Claude TUI, Codex TUI, Claude headless, and Codex headless.
- Expose three operator surfaces:
  - stepwise interactive commands for maintainers
  - unattended `auto` execution for demo-style regression
  - pack-local real-agent HTT/autotest commands
- Fail fast on missing tools, missing credential material, unsafe output-root reuse, selector-resolution gaps, and bounded phase timeouts.
- Preserve machine-readable case results, phase logs, and demo artifacts so later investigation does not require re-running the flow immediately.
- Make the pack self-contained with pack-owned `agents/`, `inputs/`, `expected_report/`, and helper scripts.
- Keep validation grounded in direct `houmao-server` HTTP routes rather than post-launch `houmao-mgr` control commands.
- Produce sanitized, snapshot-friendly artifacts so expected outputs can be tracked in git and refreshed intentionally.

**Non-Goals:**

- Making the live real-agent path part of the default fast CI suite.
- Expanding the scope to gateway attach, gateway mail, or mailbox workflows.
- Merging this workflow into the existing single-session `houmao-server-interactive-full-pipeline-demo`.
- Preserving `tests/manual/...` as the canonical operator surface.
- Introducing a second public operator API path that bypasses `houmao-server`.
- Replacing the live provider/API dependency with fake executables or synthetic success reconstruction for the HTT path.

## Decisions

### 1. Treat the four-lane `auto` flow as the canonical path worth driving end to end

The canonical direct managed-agent API validation path for this change is:

```text
run_demo.sh auto
  -> preflight
  -> start owned houmao-server
  -> provision four managed-agent lanes
  -> inspect through public server routes
  -> submit one prompt across all selected lanes
  -> verify report + sanitized snapshot contract
  -> stop lanes and owned server
```

The first implemented HTT case, `real-agent-all-lanes-auto`, will drive that same path through the pack-local `autotest/run_autotest.sh` harness with stricter preflight, bounded phase execution, and machine-readable case evidence.

Success for the canonical path means:

- the owned `houmao-server` starts and passes `/health`
- all selected lanes become visible on `/houmao/agents`
- inspect artifacts confirm the expected transport details and bounded history
- prompt requests are accepted for all selected lanes
- headless lanes leave durable turn evidence when a headless turn handle is returned
- `verify` writes raw and sanitized reports and the sanitized report matches the tracked expected report
- `stop` records cleanup outcomes for every launched lane plus owned-server shutdown

Alternative considered:

- keep `run_demo.sh` purely stepwise and let the HTT harness invent its own unattended path
  - rejected because the demo surface and the HTT surface would drift immediately

### 2. Create a new dedicated demo pack instead of extending the existing interactive full-pipeline demo

The new pack will live at `scripts/demo/houmao-server-agent-api-demo-pack/` and will have its own helper module under `src/houmao/demo/houmao_server_agent_api_demo_pack/`.

Rationale:

- the existing interactive full-pipeline demo is a single-session TUI story, not a four-lane API validation matrix
- the new pack needs lane selection, aggregate verification, and per-lane artifact management
- keeping it separate avoids collapsing two distinct maintainer workflows into one overgrown demo

Alternative considered:

- extend `houmao-server-interactive-full-pipeline-demo`
  - rejected because its mental model, state shape, and helper surface are session-centric rather than lane-centric

### 3. Make the demo pack fully pack-owned for non-secret launch inputs

The new pack will own:

- `agents/` for native selectors, tool adapters, config profile skeletons, and role prompts
- `inputs/` for prompt files, run parameters, and the minimal dummy project template
- `expected_report/` for the canonical sanitized snapshot

Rationale:

- current pair launch resolves native selectors from the effective agent-definition root, so the pack must control that root explicitly
- tutorial-pack mechanics are stronger when readers can inspect one directory and see every non-secret input required for the workflow
- this removes the current ambiguity between test fixture ownership and demo ownership

Alternative considered:

- reuse `tests/fixtures/agents/` and the existing dummy-project fixture as the startup source of truth
  - rejected because it keeps the new demo coupled to test-only layout and weakens self-containment

### 4. Keep the canonical control path fully server-owned

The pack will provision and validate lanes through direct `houmao-server` routes:

- TUI lanes: `POST /cao/sessions` plus `POST /houmao/launches/register`
- headless lanes: `POST /houmao/agents/headless/launches`
- inspect: `/houmao/agents`, `/state`, `/state/detail`, and `/history`
- request validation: `POST /houmao/agents/{agent_ref}/requests`
- headless durable inspection: `/turns/*`
- stop: `POST /houmao/agents/{agent_ref}/stop`

Rationale:

- the pack exists to validate the direct server API boundary itself
- using `houmao-mgr` for post-start interaction would convert this into a pair-CLI demo instead of an API demo
- this keeps the public authority stable even if `houmao-mgr` CLI phrasing evolves

Alternative considered:

- launch and follow up through `houmao-mgr agents ...`
  - rejected because it validates the CLI wrapper contract rather than the server contract

### 5. Separate the tutorial/demo wrapper from the HTT harness

The implementation will use three layers:

- `run_demo.sh` for pack-local operator commands
- `src/houmao/demo/houmao_server_agent_api_demo_pack/` for structured Python command logic
- `autotest/run_autotest.sh` plus `autotest/case-*.sh` / `case-*.md` for real-agent HTT runs

The harness contract will be:

```bash
scripts/demo/houmao-server-agent-api-demo-pack/autotest/run_autotest.sh \
  --case <case-id> \
  [--demo-output-dir <path>]
```

The repo is shell-first for demo wrappers, so the harness and initial case executables will use `.sh`. Shared shell functions and reusable helpers will live under `autotest/helpers/`.

`run_demo.sh` remains the operator/demo wrapper. HTT case selection belongs only to `autotest/run_autotest.sh`.

Rationale:

- this matches the repository's current tutorial-pack pattern
- it keeps shell ergonomics simple while keeping stateful orchestration and sanitization in typed Python code
- the HTT harness can stay strict about preflight, timeouts, and result logging without overloading the tutorial wrapper

Alternative considered:

- keep one Python-only CLI with no shell wrapper or dedicated autotest shell harness
  - rejected because the repository's maintained tutorial packs use `run_demo.sh` and pack-local autotest entrypoints as the operator-facing convention

### 6. Define one initial HTT case set instead of leaving the harness generic

The first implemented case set will be:

- `real-agent-preflight`
- `real-agent-all-lanes-auto`
- `real-agent-interrupt-recovery`

The design roles of those cases are:

- `real-agent-preflight`: prove the pack can validate tools, credentials, pack-owned selector inputs, output-root ownership, and other startup prerequisites before any live server or lane launch begins
- `real-agent-all-lanes-auto`: run the canonical unattended four-lane path and capture one durable pass/fail result with pointers to the generated demo artifacts
- `real-agent-interrupt-recovery`: start a tracked interrupt lane set, submit a long-running prompt fixture, issue `request_kind = interrupt`, inspect the resulting state/history evidence, and stop cleanly

The implemented `autotest/case-*.md` files are not copies of the change-owned testplans. They are operator-facing companion guides that explain how to run the implemented case, what to observe, and what success or failure looks like at each step.

Alternative considered:

- add only a single generic `live-suite` case and defer interrupt and preflight behavior to later tasks
  - rejected because the separate cases are what make preflight and interrupt behavior reviewable before implementation

### 7. Make preflight, timeout, and external-write safety explicit

The live HTT path intentionally uses the real local provider executables and real credential material, but it still needs explicit safety boundaries:

- all filesystem writes from launched lanes will be redirected into run-owned copied workdirs under the selected demo output root rather than the main repository checkout
- the pack will not attach a gateway, send mail, or hit unrelated side-effecting integrations
- pack-owned selector assets and copied workdirs will be the only non-secret startup inputs
- the harness will fail before startup if required tools, credentials, pack assets, or output-root ownership checks fail
- each live phase will have a bounded timeout budget and a clear non-zero failure outcome

When a bounded phase fails, the harness must preserve the current demo output directory, server logs, lane artifacts, and current inspect coordinates instead of attempting synthetic recovery.

Alternative considered:

- treat missing prerequisites as `SKIP` or silently reduce the lane set
  - rejected because HTT needs a hard blocker signal, not an ambiguous partial run

### 8. Default to a pack-local generated output root with explicit override

The pack will default to a generated output tree under `scripts/demo/houmao-server-agent-api-demo-pack/outputs/` and allow `--demo-output-dir <path>` overrides.

The output tree will persist:

- demo state and shared control artifacts
- per-lane launch, route, request, turn, and stop artifacts
- owned `houmao-server` logs
- sanitized verification reports
- autotest phase logs and result JSON under `control/autotest/` and `logs/autotest/<case-id>/`

Rationale:

- tutorial-pack guidance favors pack-local generated state that is easy to inspect and easy to ignore in git
- a stable pack-local output root makes interactive follow-up and autotest case inspection easier than chasing timestamp-only roots under `tests/manual/`

Alternative considered:

- preserve the current default under `tmp/tests/...`
  - rejected because it keeps the workflow visually tied to the old manual-test identity

### 9. Keep change-owned `testplans/` and implemented `autotest/` assets distinct

Before implementation, this change will carry design-owned case plans under:

- `openspec/changes/move-houmao-server-agent-api-suite-to-demo-pack/testplans/case-real-agent-preflight.md`
- `openspec/changes/move-houmao-server-agent-api-suite-to-demo-pack/testplans/case-real-agent-all-lanes-auto.md`
- `openspec/changes/move-houmao-server-agent-api-suite-to-demo-pack/testplans/case-real-agent-interrupt-recovery.md`

Those documents define goals, runner surfaces, ordered steps, expected evidence, failure signals, and Mermaid sequence diagrams for the intended cases.

During implementation, the approved plans will drive these pack-local assets:

- `scripts/demo/houmao-server-agent-api-demo-pack/autotest/run_autotest.sh`
- `scripts/demo/houmao-server-agent-api-demo-pack/autotest/case-real-agent-preflight.sh`
- `scripts/demo/houmao-server-agent-api-demo-pack/autotest/case-real-agent-preflight.md`
- `scripts/demo/houmao-server-agent-api-demo-pack/autotest/case-real-agent-all-lanes-auto.sh`
- `scripts/demo/houmao-server-agent-api-demo-pack/autotest/case-real-agent-all-lanes-auto.md`
- `scripts/demo/houmao-server-agent-api-demo-pack/autotest/case-real-agent-interrupt-recovery.sh`
- `scripts/demo/houmao-server-agent-api-demo-pack/autotest/case-real-agent-interrupt-recovery.md`
- `scripts/demo/houmao-server-agent-api-demo-pack/autotest/helpers/`

Alternative considered:

- describe the cases only in `tasks.md` and let the implementation invent the final semantics
  - rejected because the case contracts would not be reviewable before code landed

### 10. Treat the old `tests/manual` entrypoint as migratable, not canonical

The new pack becomes the canonical operator contract. The implementation may temporarily keep a delegating compatibility shim during development if needed, but the design target is to remove `tests/manual/manual_houmao_server_agent_api_live_suite.py` and its sibling package from the canonical documented path.

Rationale:

- maintaining two first-class entrypoints for the same workflow invites drift
- the purpose of the change is not to add another façade but to move the contract

## Risks / Trade-offs

- `[Pack duplication]` → Pack-owned `agents/` and `inputs/` will duplicate some existing test assets. Mitigation: keep the pack assets minimal and purpose-built instead of copying broad test trees.
- `[Long-running real-agent automation]` → Four-lane live runs can be slow or flaky on developer machines. Mitigation: keep lane selection explicit, provide stepwise commands, make the HTT harness opt-in, and keep per-phase timeouts bounded.
- `[Two runner surfaces can drift]` → `run_demo.sh auto` and `autotest/run_autotest.sh --case real-agent-all-lanes-auto` could diverge. Mitigation: make the case wrap the canonical `auto` path rather than inventing a separate flow.
- `[Snapshot churn]` → Direct live artifacts contain timestamps, ids, and paths. Mitigation: define one narrow sanitized report contract and compare only sanitized content in `expected_report/`.
- `[Real provider/API dependencies cost time and money]` → The HTT path intentionally uses live provider executables. Mitigation: keep prompts small and tracked, keep the interrupt case on a bounded lane subset, and keep the harness opt-in instead of default CI behavior.
- `[Scope creep into general pair demos]` → The workflow could drift toward the broader interactive demo or gateway demos. Mitigation: keep the pack's contract focused on direct `houmao-server` managed-agent API validation without gateway dependence.
- `[Migration confusion]` → Maintainers may still look for the old manual entrypoint. Mitigation: update docs, spec text, and any convenience wrappers to point directly at the new demo pack.

## Migration Plan

1. Write and review the change-owned `testplans/case-*.md` documents before code changes begin.
2. Create the new demo-pack directory, helper package, pack-owned inputs, and `autotest/` layout.
3. Implement pack-owned preflight, output-root safety, selector-root injection, and owned `houmao-server` startup before live-case logic.
4. Implement the canonical `run_demo.sh auto` path and wire `real-agent-all-lanes-auto` through the dedicated harness.
5. Implement the supporting `real-agent-preflight` and `real-agent-interrupt-recovery` cases plus shared `autotest/helpers/`.
6. Add pack-local README, report sanitization, expected-report verification, docs updates, and retirement of the old manual entrypoint.

Rollback strategy:

- because this repository is under active unstable development, rollback is simply to keep the old manual entrypoint in place until the new pack reaches parity; no compatibility bridge is required after the migration is accepted

## Open Questions

- Should the tracked `expected_report/` cover only the canonical all-four-lane `auto` run, or should the pack also track subset-specific snapshots? Current recommendation: track only the canonical aggregate run and leave subset runs unsnapshotted.
- Should the pack ship one dedicated dummy-project template under `inputs/`, or should it vendor a small shared helper from another demo pack? Current recommendation: use one pack-owned minimal template to keep the contract self-contained.
