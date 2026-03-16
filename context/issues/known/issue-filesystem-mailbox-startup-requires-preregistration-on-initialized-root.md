# Issue: Filesystem Mailbox Startup Effectively Requires Pre-Registration On An Initialized Root

## Summary

The current runtime mailbox startup order makes filesystem-mailbox sessions behave as if the mailbox address must already be registered before `start-session` can succeed, once the shared mailbox root has already been initialized.

This is a system-level runtime issue, not a tutorial-pack-only problem. Any workflow that starts multiple mailbox-enabled agents against the same filesystem mailbox root can hit the same failure pattern.

## What Failed

Observed during mailbox tutorial-pack testing on 2026-03-16:

- the sender session started successfully on a fresh shared mailbox root
- the receiver session then failed during `start-session`

Failure:

```text
houmao.mailbox.errors.MailboxBootstrapError: no active mailbox registration exists for `AGENTSYS-mailbox-receiver@agents.localhost`
```

## Current Behavior

- `start_runtime_session()` builds the launch plan before mailbox bootstrap runs.
- `build_launch_plan()` injects mailbox environment variables during launch-plan construction.
- mailbox env binding resolves the active filesystem inbox directory immediately.
- on an initialized mailbox root, active inbox resolution requires an existing active mailbox registration for the target address.
- the registration is only created later by mailbox bootstrap.

That means the runtime asks for the active registration before it performs the step that creates that registration.

On a brand-new mailbox root, the first mailbox-enabled agent can still start because inbox resolution takes a fallback path before mailbox protocol/index state exists.

On later startups against the same shared root, the mailbox root is already initialized, so inbox resolution becomes strict and the session fails before bootstrap can register the new principal.

Relevant files:

- `src/houmao/agents/realm_controller/runtime.py`
- `src/houmao/agents/realm_controller/launch_plan.py`
- `src/houmao/agents/mailbox_runtime_support.py`
- `src/houmao/mailbox/filesystem.py`

## Why This Matters

- Multi-agent mailbox workflows are order-dependent in a way that is not obvious from the high-level interface.
- The first agent may start successfully while later agents on the same shared mailbox root fail deterministically.
- Operators can be misled into thinking later mailbox-enabled agents must be manually pre-registered before normal startup.
- Demo and integration flows that expect several agents to join a shared filesystem mailbox during ordinary `start-session` calls are not self-contained today.
- Agents that do not request mailbox support are not affected, which makes the bug easy to misdiagnose as a scenario-specific configuration issue.

## Desired Direction

Mailbox-enabled startup on a filesystem mailbox root should not require pre-registration as an implicit prerequisite for normal `start-session`.

In practice, the runtime should be able to start a mailbox-enabled agent on an already-initialized shared mailbox root and create or confirm that agent's registration as part of normal startup, without relying on prior external registration steps.

If the implementation wants strict registration semantics after initialization, then launch-plan mailbox env binding still needs to tolerate self-registration during startup instead of requiring the registration to exist before bootstrap has run.

## Suggested Follow-Up

- Change runtime startup ordering so mailbox bootstrap or registration happens before launch-plan mailbox env binding needs the active inbox path.
- Or make filesystem mailbox env binding tolerant of a not-yet-registered address when the current startup is responsible for creating that registration.
- Add integration coverage for starting two mailbox-enabled agents sequentially against the same initialized filesystem mailbox root.
- Document clearly, until fixed, that the observed pre-registration requirement is a current implementation limitation rather than an intentional system contract.
