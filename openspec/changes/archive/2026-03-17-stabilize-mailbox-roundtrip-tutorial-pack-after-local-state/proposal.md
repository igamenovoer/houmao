## Why

The mailbox roundtrip tutorial pack was added before the mailbox-local state and gateway notifier work landed, so its current operator story is only partially aligned with the live mailbox system. The pack still assumes an externally managed CAO server, does not surface the shared `index.sqlite` versus mailbox-local `mailbox.sqlite` split clearly, and depends on runtime behavior that currently breaks when a second mailbox-enabled session joins an already initialized shared mailbox root.

Interactive testing also surfaced two system-level issues that directly affect the tutorial-pack default path:

- the runtime currently behaves as if a later mailbox-enabled agent must already be registered before `start-session` can succeed on an initialized shared mailbox root, and
- the checked-in launcher config hardcodes a non-portable `home_dir`, which makes repo-owned launcher flows brittle across developer machines.

We need one follow-up change that makes the tutorial pack truthful about the latest mailbox model, self-contained enough to run reliably, and unblocked by the system behaviors that currently make the demo fail.

## What Changes

- Refresh the mailbox roundtrip tutorial pack so its default loopback path launcher-manages a local CAO server, keeps launcher/profile-store state aligned with the demo workspace, and no longer depends on an ambient CAO service being preconfigured correctly.
- Update the tutorial README, output layout, and verification contract so the pack teaches the current mailbox storage model: shared `index.sqlite` for catalog state plus per-mailbox `mailbox.sqlite` for mailbox-view state.
- Keep the tutorial pack focused on the operator-facing `mail send -> mail check -> mail reply -> mail check` roundtrip, while documenting gateway notifier behavior as optional follow-up context rather than making gateway attachment part of the core success path.
- Fix mailbox-enabled runtime startup so a second agent can join the same initialized filesystem mailbox root without manual pre-registration.
- Make the launcher contract and checked-in local config portable by allowing an empty or omitted `home_dir` to mean the launcher-derived system-defined home.

## Capabilities

### Modified Capabilities
- `mailbox-roundtrip-tutorial-pack`: The tutorial pack becomes launcher-managed by default on loopback CAO, teaches mailbox-local state explicitly, and verifies the latest mailbox layout rather than the pre-local-state mental model.
- `brain-launch-runtime`: Mailbox-enabled `start-session` no longer requires pre-existing registration when joining an initialized shared filesystem mailbox root.
- `cao-server-launcher`: Launcher config and checked-in defaults support a portable system-defined home selection instead of requiring a host-specific absolute `home_dir`.

## Impact

- Affected code: `scripts/demo/mailbox-roundtrip-tutorial-pack/*`, `src/houmao/agents/realm_controller/runtime.py`, `src/houmao/agents/realm_controller/launch_plan.py`, `src/houmao/agents/mailbox_runtime_support.py`, `src/houmao/cao/server_launcher.py`, and `config/cao-server-launcher/local.toml`.
- Affected tests: tutorial-pack unit/integration coverage, mailbox runtime startup regression coverage for multi-agent shared roots, and launcher config validation coverage.
- Affected operator behavior: the mailbox tutorial becomes self-managed for local CAO by default, the repo-owned launcher config becomes portable, and the shared-mailbox two-agent bring-up no longer behaves as if later agents require manual pre-registration.
