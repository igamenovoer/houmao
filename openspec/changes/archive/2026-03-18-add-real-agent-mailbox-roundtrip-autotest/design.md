## Context

The current mailbox tutorial pack already has strong pack-local automation mechanics, but its live-coverage story is split in a way that is not HTT-ready. The deterministic automation lanes remain useful for regression, yet they do not use actual local agents or real credentials. The separate manual smoke script does use local tools, but it is not the canonical pack-owned automation surface and it does not define stable per-case evidence or case playbooks inside the tutorial pack itself.

The requested workflow is stricter than the current manual-smoke promise: it must use real agents, one agent must send actual mail to the other through the direct runtime mail path, and the completed run must leave final mailbox files on disk so a maintainer can inspect them afterward. That means the canonical automation surface must move from "manual smoke around the pack" to a pack-owned real-agent harness that is separate from the operator-oriented `run_demo.sh` flow.

This change also needs a clearer artifact split than earlier revisions: the OpenSpec change's `testplans/` directory is for design-phase planning only, while the final tutorial-pack implementation should expose operator-facing assets under `autotest/`. Those implemented Markdown files are companion/readme documents for the runnable shell cases, not copies of the design-phase testplans.

This design assumes the dummy-project and lightweight mailbox-demo fixture direction remains valid. If the active `use-dummy-project-fixtures-and-mailbox-demo-roles` change lands first, this change should build on it directly. If it does not, implementation should fold the same fixture assumptions into this work rather than reverting to the main repository worktree.

## Goals / Non-Goals

**Goals:**

- Expose one canonical non-interactive real-agent harness surface from the mailbox tutorial pack itself without adding HTT-only subcommands to `run_demo.sh`.
- Use actual local `claude` and `codex` executables plus real credential profiles for the canonical HTT case.
- Fail fast on missing tools, missing credential material, unsafe or incompatible runtime ownership, and bounded-turn timeout exhaustion.
- Preserve raw mailbox artifacts, inspection pointers, and machine-readable case evidence after `stop` so maintainers can inspect the final mail files on disk.
- Capture each supported auto-test case first as a change-owned `testplans/case-*.md` document before implementation, then implement pack-local `autotest/` assets where `.sh` files execute the cases and `.md` files document the implemented behavior for operators.

**Non-Goals:**

- Make real-agent mailbox autotests part of the default fast CI suite.
- Remove deterministic fake-cli regression coverage from the repository entirely.
- Introduce new synthetic mailbox delivery shortcuts, gateway transport fallbacks, or fake result reconstruction for the HTT path.
- Generalize the real-agent harness surface into a cross-repository framework beyond this tutorial pack.

## Decisions

### Decision: Add a separate `autotest/run_autotest.sh` harness as the canonical HTT runner surface

The tutorial pack will gain a dedicated harness script under its implemented autotest tree, `autotest/run_autotest.sh`, rather than overloading `run_demo.sh` with HTT-only subcommands. `autotest/run_autotest.sh` will be opt-in, case-based, and clearly reserved for real-agent hack-through-testing runs.

The preferred invocation shape is:

```bash
scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/run_autotest.sh --case <case-id> --demo-output-dir <path>
```

The first implementation should support `real-agent-roundtrip` as the default case when `--case` is omitted. Later supported cases should use the same command surface.

This keeps `run_demo.sh` focused on the tutorial/demo operator flow while giving the real-agent HTT path its own explicit harness boundary.

**Alternatives considered**

- Add `--real-agents` to `auto`: rejected because it overloads one command with two very different safety and evidence models.
- Add `autotest` as a `run_demo.sh` subcommand: rejected because HTT harness concerns should not be bundled into the operator/demo wrapper.
- Keep the manual smoke script as the only real-agent entrypoint: rejected because HTT needs a pack-owned canonical path, not an outer wrapper with ad hoc reporting.

### Decision: The canonical case will be one real sender-to-receiver roundtrip with actual local binaries and real credential profiles

`real-agent-roundtrip` is the first path worth driving end to end. The separate harness will:

1. run preflight,
2. start sender and receiver through the real `start-session` path,
3. publish pack-local inspect commands for both agents,
4. execute `mail send -> mail check -> mail reply -> mail check`,
5. run verification, and
6. stop the sessions without removing the mailbox artifacts.

The canonical case must resolve the actual local `claude` and `codex` executables on `PATH` and the actual credential profiles selected by the demo blueprints or explicit overrides. Fake executables, fake credential stores, or synthetic stand-ins do not satisfy this case.

The manual smoke script should become a thin wrapper over the pack-owned `autotest/run_autotest.sh` harness, or be removed if it no longer adds distinct value.

**Alternatives considered**

- Keep fake executables in the "live" path but rename the docs: rejected because the user journey still would not exercise real agents.
- Drive mail delivery by mailbox file injection once sessions are up: rejected because the direct runtime mail path is the point of the exercise.

### Decision: Preflight, timeout, and stop behavior will be explicit and fail fast

HTT is only useful when it quickly reveals the next real blocker. Before any live session starts, the `autotest/run_autotest.sh` harness must verify:

- `pixi`, `tmux`, `claude`, and `codex` are available,
- the selected credential profile material exists and is readable,
- the selected demo output directory is fresh or safely reusable for the chosen case,
- the CAO base URL is owned and supported for the selected run, and
- any required registry/runtime roots are isolated from unrelated local state.

During live execution, each phase must have bounded timeout behavior. A timed-out phase must fail explicitly, preserve the current demo output tree, and print the existing `inspect` commands or equivalent persisted coordinates instead of synthesizing success.

`stop` remains part of the successful path, but it must not delete the mailbox/messages or mailbox/mailboxes evidence that the case is meant to inspect after completion.

**Alternatives considered**

- Let missing prerequisites degrade to `SKIP:` semantics for the real-agent path: rejected because HTT requires a hard blocker signal, not a soft skip.
- Rely on unbounded provider latency and manual observation: rejected because it defeats the purpose of non-interactive blocker discovery.

### Decision: Case evidence will separate raw mailbox artifacts from sanitized summaries

Every harness-driven case should write a machine-readable result artifact under the selected demo output tree, for example under `control/testplans/`. The result must record enough stable evidence to locate the completed roundtrip without re-running it:

- case id,
- selected demo output directory,
- sender and receiver addresses,
- canonical send and reply message ids,
- canonical send and reply message paths,
- mailbox directory paths for both participants,
- command/status summary, and
- timeout or failure diagnostics when applicable.

The existing sanitized report contract stays separate. Raw message bodies should remain on disk in the mailbox tree for maintainer inspection, while the sanitized comparison outputs remain safe for tracked snapshots.

**Alternatives considered**

- Reuse only the sanitized report as the autotest proof: rejected because it intentionally excludes the raw mailbox content the user wants to inspect.
- Store evidence only in stdout/stderr logs: rejected because the case needs durable machine-readable pointers after the run ends.

### Decision: Change-owned testplans and implemented autotest assets have different roles

Before implementation, this change will carry explicit case plans under:

- `openspec/changes/add-real-agent-mailbox-roundtrip-autotest/testplans/case-real-agent-roundtrip.md`
- `openspec/changes/add-real-agent-mailbox-roundtrip-autotest/testplans/case-real-agent-preflight.md`
- `openspec/changes/add-real-agent-mailbox-roundtrip-autotest/testplans/case-real-agent-mailbox-persistence.md`

These files are design-owned pre-implementation testplans for the supported cases. Each testplan must describe prerequisites, invocation shape, ordered steps, expected evidence, and failure signals.

During implementation, the approved testplans should drive pack-local `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/` assets plus one harness:

- `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/run_autotest.sh`
- `autotest/case-*.sh` for the executable implementation of each case
- `autotest/case-*.md` as the operator-facing companion/readme for each implemented case
- `autotest/helpers/` for shared shell libraries and reusable helper functions used by multiple cases

The implemented companion Markdown files are not required to mirror the design-phase testplans line by line. They should explain how to run, inspect, and interpret the implemented shell cases. The `autotest/run_autotest.sh` harness owns case selection, shared preflight orchestration, result-path conventions, and dispatch into `autotest/case-*.sh`. Shared shell libraries and helper functions that serve multiple cases should live under `autotest/helpers/` and be sourced by the harness or case scripts instead of being duplicated inline. The harness may call `run_demo.sh` internally for underlying demo steps, but HTT case selection must not be exposed as `run_demo.sh` subcommands.

The initial case set intentionally separates:

- the canonical success path (`real-agent-roundtrip`),
- the fail-fast prerequisite probe (`real-agent-preflight`), and
- the post-stop mailbox inspection audit (`real-agent-mailbox-persistence`).

**Alternatives considered**

- Keep the case descriptions only inside `tasks.md` or the README: rejected because HTT case plans need dedicated reviewable documents before implementation.
- Write tutorial-pack `autotest/case-*.md` and `autotest/case-*.sh` files before the runner exists: rejected because those files belong to implementation output, while the case design needs to live under the OpenSpec change first.
- Document only the canonical case: rejected because HTT also depends on a crisp preflight and a post-stop artifact audit.

## Risks / Trade-offs

- [Real-agent autotests are slower and more failure-prone than stand-in coverage] -> Mitigation: keep them opt-in, fail fast, and preserve inspectable evidence rather than silently retrying through synthetic paths.
- [Local credential and tool differences can create environment-specific failures] -> Mitigation: make preflight explicit, machine-readable, and case-owned so failures are diagnosable before sessions start.
- [Two automation stories can confuse maintainers] -> Mitigation: clearly separate `run_demo.sh` demo/operator flows from `autotest/run_autotest.sh` HTT harness flows in docs, command names, and spec language.
- [Implemented companion Markdown can drift from design-phase testplans] -> Mitigation: treat the change-owned `testplans/` as the design source of truth and require implementation review to confirm the `autotest/` docs still represent the shipped behavior accurately.
- [Shared shell logic can sprawl across case scripts] -> Mitigation: require common helper functions and shared shell utilities to live under `autotest/helpers/` and keep case scripts thin.
- [Retaining raw mailbox artifacts increases local-state footprint] -> Mitigation: keep them under the selected demo output root and require explicit output-dir ownership instead of scattering them across ambient state.
- [This change can overlap the active dummy-project/mailbox-demo fixture change] -> Mitigation: build on that change when available and avoid reintroducing the main-repo workdir path.

## Migration Plan

1. Write and review the change-owned `testplans/case-*.md` documents before code changes begin.
2. Add `autotest/run_autotest.sh` as a dedicated harness with `--case` selection and per-case result artifacts.
3. Implement explicit real-agent preflight and timeout behavior before landing the canonical roundtrip case.
4. Implement `real-agent-roundtrip`, `real-agent-preflight`, and `real-agent-mailbox-persistence` so they use actual local tools and preserve raw mailbox evidence after stop.
5. Implement `autotest/helpers/` shared shell utilities plus `autotest/case-*.sh` and companion `autotest/case-*.md` assets informed by the approved change-owned testplans, wire them through `autotest/run_autotest.sh`, then update README and direct-live documentation so only the real-agent harness path claims the HTT/live requirement.

## Open Questions

- Should `autotest/run_autotest.sh` default to one timestamped demo output directory when `--demo-output-dir` is omitted, or should the real-agent harness require an explicit caller-owned output root every time?
- Which credential-profile override surface should be considered stable if maintainers need something narrower than the pack defaults?
