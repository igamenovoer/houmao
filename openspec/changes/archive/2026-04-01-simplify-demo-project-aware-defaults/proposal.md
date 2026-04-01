## Why

`make-operations-project-aware` changed maintained local flows so runtime, jobs, and mailbox defaults derive from the active overlay. The supported demo and helper surfaces have not fully caught up, so some of them still export multiple root env vars only to keep one demo run self-contained, even when the overlay-local contract now provides that behavior directly.

The remaining 4.5 work is to simplify the maintained demo surface, not to redesign CLI behavior again. The supported demos should keep only the overrides that still express real demo requirements, and stop teaching or depending on root-env scaffolding that is now redundant.

## What Changes

- Modify the supported `scripts/demo/minimal-agent-launch/` workflow so it uses one generated project-aware overlay as the local state anchor instead of exporting separate agent-definition and runtime root env vars only to keep the run self-contained.
- Modify the supported `scripts/demo/single-agent-mail-wakeup/` workflow so it keeps using its redirected overlay root for project-local state but drops redundant agent-definition, runtime, and jobs overrides where overlay-local defaults now suffice.
- Update maintained demo layouts, generated-output descriptions, helper code, and tests so they match the simplified project-aware default contract.
- Keep archived `scripts/demo/legacy/` material out of scope, and keep explicit registry isolation or other overrides only where they still represent an intentional demo requirement rather than redundant local-root wiring.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `minimal-agent-launch-demo`: Change the maintained minimal demo contract so the generated run tree relies on one project-aware overlay root for local Houmao-owned state instead of separate root env overrides for agent definitions and runtime placement.
- `single-agent-mail-wakeup-demo`: Change the maintained wake-up demo contract so redirected overlay state remains the authority for project-local runtime, jobs, and mailbox placement by default, while only truly necessary explicit demo overrides remain.

## Impact

- Affected code is centered in [scripts/demo/minimal-agent-launch/scripts/run_demo.sh](/data1/huangzhe/code/houmao/scripts/demo/minimal-agent-launch/scripts/run_demo.sh), [scripts/demo/minimal-agent-launch/tut-agent-launch-minimal.md](/data1/huangzhe/code/houmao/scripts/demo/minimal-agent-launch/tut-agent-launch-minimal.md), [src/houmao/demo/single_agent_mail_wakeup/runtime.py](/data1/huangzhe/code/houmao/src/houmao/demo/single_agent_mail_wakeup/runtime.py), [src/houmao/demo/single_agent_mail_wakeup/models.py](/data1/huangzhe/code/houmao/src/houmao/demo/single_agent_mail_wakeup/models.py), [scripts/demo/single-agent-mail-wakeup/README.md](/data1/huangzhe/code/houmao/scripts/demo/single-agent-mail-wakeup/README.md), and focused demo tests.
- Affected specs are the maintained demo capabilities for `minimal-agent-launch-demo` and `single-agent-mail-wakeup-demo`.
- The change may alter generated demo output paths for runtime and jobs artifacts, so tutorial text, README output-layout descriptions, expected reports, and focused demo assertions must move together.
