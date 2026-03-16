## Context

The latest mailbox system change intentionally split filesystem mailbox storage into shared catalog state plus mailbox-local view state, and it made gateway mail notifier an optional capability layered on top of mailbox truth. The current mailbox roundtrip tutorial pack still has the right high-level purpose, but it does not yet encode three key realities of the live system:

- the operator-facing roundtrip should still work without gateway attachment,
- mailbox-view state now lives in per-mailbox `mailbox.sqlite`, not in shared-root `index.sqlite`, and
- the demo is only as reliable as the runtime and launcher setup it depends on.

The tutorial-pack failures we observed were not just documentation drift. They exposed that the default demo path still relies on ambient CAO setup and that mailbox-enabled runtime startup currently has an ordering bug when two agents share one initialized filesystem mailbox root.

## Goals / Non-Goals

**Goals**

- Keep the mailbox roundtrip tutorial pack aligned with the latest mailbox storage contract and operator guidance.
- Make the default loopback demo path self-contained enough to manage CAO launcher lifecycle and CAO profile-store alignment automatically.
- Fix the runtime mailbox startup ordering bug so the tutorial's two-agent shared-root flow succeeds without manual pre-registration.
- Make the checked-in launcher config portable across developer machines by supporting a system-defined launcher home when `home_dir` is omitted or blank.

**Non-Goals**

- Turning the mailbox roundtrip tutorial pack into the primary gateway-notifier demo.
- Making gateway attachment or notifier enablement a prerequisite for the core mailbox roundtrip success path.
- Replacing the tutorial's explicit runtime `mail` flow with direct managed-script invocation.
- Introducing a large generic multi-agent CAO demo framework beyond what this pack needs.

## Decision 1: Keep the tutorial pack focused on direct runtime mail flow, not gateway notifier

The primary success path for `scripts/demo/mailbox-roundtrip-tutorial-pack` should remain:

1. build sender and receiver brains,
2. start two mailbox-enabled sessions,
3. `mail send`,
4. receiver `mail check`,
5. `mail reply`,
6. sender `mail check`,
7. stop both sessions.

The pack should be updated to explain the current mailbox-local state model and gateway optionality, but it should not require gateway attach or notifier enablement as part of the core tutorial. That keeps the pack aligned with the mailbox design constraint that gateway is optional and that agents can still process and mark mail explicitly without gateway participation.

Alternatives considered:

- Fold gateway attach and notifier enablement into the default tutorial flow.
  Rejected because it would blur the line between mailbox truth and gateway-owned reminder behavior, and it would turn a linear mailbox tutorial into a mixed mailbox-plus-gateway operator exercise.
- Ignore gateway/notifier completely.
  Rejected because the README should still explain that notifier is a separate optional capability introduced by the latest mailbox change, even if it is not part of the core walkthrough.

## Decision 2: The tutorial runner should own loopback CAO lifecycle with a demo-local launcher config

For supported loopback CAO URLs, the tutorial runner should generate a demo-local launcher config and use helper-owned Python logic in `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/tutorial_pack_helpers.py` to start or reuse CAO through `houmao.cao.tools.cao_server_launcher`, perform ownership checks, align profile-store selection, and handle cleanup on exit.

The recommended layout is:

```text
<demo-output-dir>/
├── project/
├── runtime/
├── shared-mailbox/
├── cao/
│   ├── launcher.toml
│   └── runtime/
│       └── cao_servers/<host>-<port>/
│           ├── launcher/
│           └── home/
└── report*.json
```

This pattern reuses the repo's existing launcher-managed demo shape instead of assuming an ambient CAO server at `localhost:9889` is already configured with the right workdir policy, ownership context, and profile store.

Keeping the default base URL on the familiar loopback port is still reasonable for manual readability and compatibility, but the runner should actively manage ownership and stop or restart stale reused servers when necessary rather than silently depending on whatever is already listening.

The bash wrapper should remain a thin orchestration layer. Structured launcher concerns such as config generation, ownership verification, resolved profile-store selection, and "did this run start CAO?" state should live in the Python helper so the lifecycle remains testable and so interrupted or partial-start cleanup behavior is owned in one place.

Alternatives considered:

- Keep requiring a pre-existing external CAO server.
  Rejected because the tutorial pack has already shown that ambient CAO ownership, workdir policy, and profile-store state are too fragile for a default operator walkthrough.
- Pick a random loopback port on every run.
  Rejected for the first pass because it complicates the manual walkthrough and is less friendly to environments that still assume the common default port, while ownership-aware launcher management already addresses the main reuse problem.

## Decision 3: The tutorial should verify and explain mailbox-local state explicitly

The tutorial README, sanitized report, and verification flow should make the mailbox-local state split visible:

- shared `index.sqlite` remains the shared mailbox-root catalog,
- each resolved mailbox directory owns `mailbox.sqlite`,
- the demo should verify that both tutorial participants received mailbox-local state artifacts,
- the tutorial should describe `mailbox.sqlite` as mailbox-view state rather than implying all mutable state still lives in the shared root.

This does not require the pack to manipulate SQLite directly. The operator workflow remains runtime-owned `mail` commands. The report and docs simply need to stop teaching the stale storage model.

Verification should stay helper-owned as well: the tutorial should resolve mailbox-local SQLite paths through the mailbox module's path-resolution contract rather than hardcoding `mailboxes/<address>/mailbox.sqlite` probes in bash.

## Decision 4: Runtime mailbox bootstrap must happen before env binding resolution depends on active registration

The root cause of the receiver startup failure is ordering:

```text
current
-------
resolve mailbox config
build launch plan
  -> mailbox env bindings
     -> active inbox lookup
bootstrap mailbox registration

needed
------
resolve mailbox config
bootstrap or confirm mailbox registration
build launch plan
  -> mailbox env bindings
     -> active inbox lookup succeeds
```

The recommended fix is to compute the session manifest path early enough that mailbox bootstrap can run before launch-plan construction. That keeps registration creation in the runtime-owned bootstrap path instead of teaching `mailbox_env_bindings()` to guess or partially synthesize registration state.

This change should preserve strict registration-dependent path resolution. The runtime contract should be "bootstrap before deriving registration-dependent env bindings," not "derive best-effort paths when registration is missing." A small invariant comment near `mailbox_env_bindings()` or the reordered startup path is enough to make that assumption visible to future maintainers.

Alternatives considered:

- Make mailbox env binding tolerant of a missing self-registration and keep bootstrap later.
  Rejected as the primary approach because it preserves an awkward split where launch-plan construction still depends on state that startup is about to create. Early bootstrap is a cleaner runtime contract.

## Decision 5: Empty or omitted launcher `home_dir` should mean system-defined launcher home

The launcher already has a natural derived home location under `runtime_root/cao_servers/<host>-<port>/home`. The checked-in repo config should be able to opt into that default without hardcoding a machine-specific absolute path.

The recommended contract is:

- `home_dir` omitted -> use the launcher-derived default home
- `home_dir = ""` -> normalize to the same launcher-derived default home
- explicit non-empty `home_dir` -> use that exact absolute or config-relative path

That lets repo-owned configs express an intentional portable default while preserving explicit override support for operators who want CAO state rooted elsewhere.

The checked-in `config/cao-server-launcher/local.toml` should use explicit `home_dir = ""` to exercise that portable-default contract directly instead of only documenting it in comments. This also gives implementers a clear target for the required validator change, because `_LauncherConfigModel._validate_home_dir` currently rejects blank strings.

## Consequences

- The mailbox tutorial becomes more self-contained and operator-friendly, but it now owns more launcher setup inside the wrapper.
- The runtime fix is small in surface area but important in behavior: it changes the point at which mailbox bootstrap happens during `start-session`.
- The launcher contract becomes friendlier for checked-in configs and demos, and it removes the current `/data/agents/cao-home` portability trap.
- Gateway notifier remains documented but intentionally out of the tutorial's critical path, which keeps the demo aligned with the system's “gateway is optional” rule.
