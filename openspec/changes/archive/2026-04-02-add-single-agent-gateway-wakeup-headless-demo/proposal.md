## Why

The current supported gateway wake-up demo is explicitly TUI-only, which makes it the wrong place to teach or validate the runtime-owned headless workflow even though Houmao already supports tmux-backed headless sessions and gateway attach for native headless backends. A separate maintained demo is needed so operators can exercise the headless mailbox wake-up path without weakening the existing TUI demo contract or mixing two different operator models into one pack.

## What Changes

- Add a new supported demo under `scripts/demo/single-agent-gateway-wakeup-headless/` for one `houmao-mgr project easy` headless specialist that wakes on filesystem mailbox delivery through a live gateway mail notifier.
- Define a tmux-backed headless operator workflow with one demo-owned tmux session that keeps the headless agent in a stable agent window and the gateway in a separate watchable auxiliary window.
- Preserve the current project-local overlay model from the TUI demo: copied project under `outputs/project/`, redirected Houmao overlay under `outputs/overlay/`, demo-local registry override, and reusable overlay-backed specialist/auth/setup state across fresh runs.
- Support automatic and stepwise workflows for maintained headless lanes, including `start`, `attach`, `watch-gateway`, `send`, `notifier ...`, `inspect`, `verify`, and `stop`.
- Verify completion through gateway notifier evidence, headless managed-agent state or turn evidence, deterministic project artifact creation, and actor-scoped unread completion.
- Publish the new demo from `scripts/demo/README.md` as part of the supported demo surface.
- Keep the existing `single-agent-mail-wakeup/` demo as the maintained TUI specialist demo rather than broadening its contract to cover headless behavior.

## Capabilities

### New Capabilities
- `single-agent-gateway-wakeup-headless-demo`: Supported tmux-backed headless gateway wake-up demo surface for one project-local specialist, including automatic and stepwise workflows, demo-owned output layout, and verification contract.

### Modified Capabilities

## Impact

- Affected code: new demo pack under `scripts/demo/`, new `houmao.demo` implementation modules, demo runner wiring, and new unit/demo coverage.
- Affected docs: `scripts/demo/README.md` and the new demo README.
- Affected systems: `project easy` specialist and instance launch flows, managed-agent headless runtime control, live gateway attach/notifier behavior, filesystem mailbox delivery, and demo verification/reporting.
- Dependencies and constraints: the initial maintained demo contract should align with currently supported unattended headless lanes; Gemini headless inclusion depends on establishing a maintained unattended launch-policy path rather than assuming it implicitly.
