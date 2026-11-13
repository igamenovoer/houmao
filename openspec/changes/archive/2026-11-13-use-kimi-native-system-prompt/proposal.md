## Why

Houmao currently delivers Kimi role prompts through a managed auto-skill workaround because the maintained Kimi line lacked a native system-prompt surface. Kimi Code 0.34 provides `$KIMI_CODE_HOME/SYSTEM.md`, so retaining the workaround and pre-0.34 behavior would create two launch contracts and preserve a prompt-delivery path that can silently fail before the first substantive turn.

## What Changes

- **BREAKING** Raise the maintained Kimi Code floor to 0.34.0 and reject earlier versions during launch-policy selection. Kimi support has no upper version limit.
- Deliver the complete composed Houmao role prompt through Kimi's native `$KIMI_CODE_HOME/SYSTEM.md` contract while preserving Kimi's built-in prompt through `${base_prompt}` and forcing the v2 engine.
- Make the Kimi prompt projection deterministic and inspectable: reject every `${identifier}` placeholder in Houmao prompt text so later Kimi releases cannot reinterpret it, remove stale managed files when no role prompt applies, record provenance, and reject agent-selection inputs that would bypass `SYSTEM.md`.
- **BREAKING** Remove the `houmao-auto-system-prompt` package, managed auto-skill projection, and the public `houmao-mgr agents self system-prompt show` retrieval command that existed only to support that workaround.
- Refresh Kimi launch, TUI tracking, recorded evidence, developer qualification, README, and reference documentation around the native contract introduced at 0.34.0, with no compatibility path for older Kimi releases and no upper version cap.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: Replace Kimi bootstrap and managed auto-skill role delivery with native home-level system-prompt projection and explicit conflict checks.
- `versioned-launch-policy-registry`: Replace the Kimi 0.23.x strategy and auto-skill capability flags with a minimum-version `>=0.34.0` native-system-prompt contract.
- `managed-agent-auto-skills`: Remove the managed auto-skill lane and the `houmao-auto-system-prompt` package contract.
- `houmao-mgr-agents-scope-cli`: Remove effective-system-prompt retrieval from the public `agents self` surface.
- `houmao-system-skill-installation`: Remove managed auto skills as a separate installation-policy category.
- `houmao-system-skill-version-metadata`: Remove the deleted auto prompt package from version-contract exclusions and doctor scenarios.
- `houmao-mgr-system-skills-cli`: Remove managed auto skills from the CLI's install-unit boundary language.
- `houmao-dev-behavior-testing-skill`: Replace managed auto-skill qualification inputs and evidence with native provider system-prompt projection evidence.
- `houmao-dev-behavior-testing-coverage-profiles`: Remove the deleted managed auto-skill projection category from development-only coverage boundaries.
- `houmao-dev-tui-testing-skill`: Remove the deleted managed auto-skill projection category from development-only skill boundaries.
- `kimi-code-tui-support`: Raise the maintained Kimi TUI minimum to 0.34.0 and require the native role prompt to be in place before session startup.
- `kimi-tui-signal-corpus`: Requalify the maintained unattended corpus against Kimi 0.34.x.
- `versioned-tui-signal-profiles`: Replace maintained Kimi 0.23.x profiles with a profile selected for every Kimi version at or above 0.34.0 and remove pre-0.34 compatibility.
- `shared-tui-tracking-recorded-validation`: Move current Kimi recorded validation from 0.23.x to 0.34.x.
- `docs-build-phase-reference`: Document the Kimi 0.34.0 minimum and native system-prompt build contract, with no upper limit, and remove workaround guidance.
- `docs-run-phase-reference`: Document native Kimi role injection and the minimum-version runtime boundary.
- `docs-getting-started`: Present Kimi 0.34.0 as the minimum maintained release with no upper limit and remove manual auto-skill instructions.
- `docs-launch-policy-reference`: Update maintained Kimi headless and TUI policy documentation to the `>=0.34.0` native role-injection contract.
- `docs-cli-reference`: Remove the deleted auto-skill and self-prompt command from CLI reference requirements.
- `docs-readme-system-skills`: Remove the deleted auto prompt package from README system-skill boundary requirements.
- `readme-structure`: Replace Kimi auto-skill guidance with the Kimi `>=0.34.0` native prompt contract and breaking version floor.

## Impact

This change affects Kimi version selection and launch-policy data, brain construction and rebuild behavior, launch-plan validation, Kimi home contents and manifests, the CAO Kimi compatibility adapter, TUI signal profiles and fixtures, system-skill and developer-qualification metadata, the `houmao-mgr agents self` CLI, tests, README, and build/run/CLI/getting-started documentation. Existing Kimi brains built for releases before 0.34 must be rebuilt and relaunched with Kimi Code 0.34.0 or later; existing sessions receive no migration or resume compatibility guarantee.
