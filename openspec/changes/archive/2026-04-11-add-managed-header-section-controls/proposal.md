## Why

The current managed prompt header is controlled as one enabled/disabled block, but the content is already conceptually made of separate guidance areas: managed identity and Houmao runtime guidance. We need to make those areas explicit, add a default-on automation notice plus default-off task reminder and mail acknowledgement notices, and give operators a narrow way to enable or disable individual sections without losing the whole managed-header contract.

## What Changes

- Split the rendered managed prompt header into named sections with deterministic ordering.
- Add a default-enabled automation notice section that applies to all managed launches, including launches whose provider startup policy is `as_is`.
- Add a default-disabled task reminder section that tells agents to create and later cancel a one-off live gateway reminder for potentially long-running work.
- Add a default-disabled mail acknowledgement section that tells agents to send an acknowledgement to the reply-enabled address for mailbox-driven work.
- Make the automation notice explicitly prohibit Claude's `AskUserQuestion` tool and equivalent interactive user-question tools that would open or focus an operator TUI panel.
- Direct agents doing mailbox-driven work to use reply-enabled mailbox threads for clarification instead of asking the interactive operator; when a mailbox thread is not reply-enabled, the agent must decide autonomously from available context.
- Add stored launch-profile and easy-profile section-level policy controls while preserving existing `--managed-header` / `--no-managed-header` whole-header behavior.
- Add one-shot launch section overrides for `houmao-mgr agents launch` and `houmao-mgr project easy instance launch`.
- Persist secret-free section decision metadata with the managed prompt layout so relaunch/debug surfaces can explain which sections were enabled and why.
- Update docs and CLI reference coverage for managed-header sections and the automation notice.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `managed-launch-prompt-header`: split the header into named sections, add the automation notice, task reminder, and mail acknowledgement sections, define section default behavior, and persist section decision metadata.
- `houmao-mgr-agents-launch`: add one-shot managed-header section override flags to direct and launch-profile-backed managed launches.
- `houmao-mgr-project-agents-launch-profiles`: add persistent section-policy controls to explicit project launch-profile create/set/get flows.
- `houmao-mgr-project-easy-cli`: add persistent easy-profile section-policy controls and one-shot easy-instance launch section overrides.
- `docs-managed-launch-prompt-header-reference`: document the section model, per-section default behavior, automation notice, task reminder notice, mail acknowledgement notice, and CLI controls.
- `docs-cli-reference`: document the new section-level managed-header flags on relevant CLI surfaces.
- `docs-launch-profiles-guide`: explain how stored launch profiles persist managed-header section policy and how that interacts with whole-header policy.

## Impact

- Affected prompt code: `src/houmao/agents/managed_prompt_header.py` and launch composition in `src/houmao/srv_ctrl/commands/agents/core.py`.
- Affected storage and payloads: project catalog launch-profile persistence and launch-profile payload rendering.
- Affected CLI surfaces: `houmao-mgr agents launch`, `houmao-mgr project agents launch-profiles add/set/get`, `houmao-mgr project easy profile create/set/get`, and `houmao-mgr project easy instance launch`.
- Affected tests: managed prompt header unit tests, project command tests, agents launch command tests, and CLI shape/reference tests.
- Affected docs: managed prompt header reference, launch profile guide, and generated/static CLI reference.
