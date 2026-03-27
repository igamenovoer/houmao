## Why

`gateway-mail-wakeup-demo-pack` still teaches and verifies the older CAO-owned control path even though the repository now treats `houmao-server` plus managed-agent gateway routes as the supported control plane. That drift makes the pack a weak regression target for current Houmao behavior and risks leaving the demo broken or misleading as the rest of the system continues moving away from raw `cao_rest` operator flows.

## What Changes

- Migrate `gateway-mail-wakeup-demo-pack` from demo-owned CAO launcher management to demo-owned `houmao-server` lifecycle management.
- Change the pack's default started session from `backend=cao_rest` to the supported pair-backed `backend=houmao_server_rest`.
- Update the pack's start, idle-wait, gateway attach, notifier control, inspection, and stop flows so they align with the current post-launch attach model and server-backed managed-agent authority.
- Refresh the pack's report contract, README, and regression tests so they verify server-backed lifecycle evidence instead of CAO-specific launcher and terminal evidence.
- Add explicit project-local mailbox skill staging for the copied dummy-project workdir so unattended mailbox wake-up turns remain reliable under the current Codex/runtime mailbox-skill model.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `gateway-mail-wakeup-demo-pack`: change the demo pack requirements so the runnable wake-up walkthrough uses a demo-owned `houmao-server` plus `houmao_server_rest` session flow, verifies the newer server-backed control surfaces, and stages runtime mailbox skills into the copied dummy-project workdir.

## Impact

- Affected code: `scripts/demo/gateway-mail-wakeup-demo-pack/*`, pack-local helper scripts, and `tests/unit/demo/test_gateway_mail_wakeup_demo_pack.py`
- Affected docs: gateway lifecycle/reference docs that point readers at this pack as the runnable wake-up walkthrough
- Affected systems: demo-owned server lifecycle, runtime session startup for the pack, post-launch gateway attach, notifier inspection, and mailbox-skill projection for the copied demo project
