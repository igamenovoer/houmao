# Proposal

## Why

Houmao cannot currently launch or control Hermes Agent. Hermes exposes structured interfaces for its terminal UI, ACP service, and one-shot CLI, so Houmao can manage all three without reading terminal text.

## What Changes

- Add Hermes as an installed native tool with `tui`, `service`, and `headless` run modes. Use `service` as the managed launch default when no mode is selected. Reject Hermes `web` launches during preflight.
- Launch the real Hermes TUI in tmux and use its private native RPC for prompt submission, state, events, and interruption. Bind the managed conversation before opening the terminal.
- Use `hermes acp` in service mode and the one-shot JSONL CLI in headless mode. Supervise the Hermes daemon that executes turns and preserve exact continuation and request ownership across clients.
- For Hermes TUI, check native readiness immediately before submission. If a human turn starts after that check, retain and track Hermes's accepted queue entry. Give manager, gateway, AG-UI, mail, and CCCC the same admission behavior and distinguish native queue acceptance from turn start and completion.
- Materialize private Hermes role, skills, provider configuration, and session state using the selected Houmao launch profile. Qualify the installed Hermes v0.23.4 build locally with explicit credentials and desktop-control and browser tools excluded.

## Capabilities

### New Capabilities

- `hermes-agent-runtime` defines Hermes launch configuration, exact conversation binding, per-mode control, and native lifecycle evidence.

### Modified Capabilities

- `native-cli-provider-support` adds Hermes to the maintained provider set for its qualified modes.
- `houmao-system-skill-installation` projects selected public skill packs into managed Hermes homes.
- `agent-model-selection` treats the qualified Hermes model and route as session-bound launch inputs.
- `managed-agent-run-modes` defines Hermes mode selection and allows a finite headless CLI to use an owned native daemon.
- `brain-launch-runtime` distinguishes finite client exit from native turn settlement.
- `managed-agent-detailed-state` reports structured Hermes TUI state and keeps unresolved headless work visible after CLI exit.
- `official-tui-state-tracking` scopes terminal-text tracking to parser-backed TUI runtimes.
- `passive-server-tui-observation` selects terminal parsers only for eligible parser-backed targets.
- `passive-server-headless-management` admits Hermes on the qualified headless birth route and settles turns using attributable native evidence.
- `agent-gateway` defines Hermes TUI native readiness, tracked queue acceptance, and structured dispatch.
- `gateway-plugin-api` lets a verified Hermes-native queue receipt confirm an ordinary event handoff after the idle check.
- `agent-gateway-mail-notifier` uses Hermes native readiness and correlates the accepted reminder until settlement.
- `cccc-external-receiver` recognizes a qualified native queued handoff for an exact CCCC batch.
- `per-agent-ag-ui-run-streaming` uses Hermes TUI's structured events and waits for request-correlated terminal evidence.
- `test-agent-launch-fixtures` adds explicit Hermes provider selection and raw and managed fixture lanes for each supported mode.

## Impact

- Agent definitions, native home preparation, launch policy and model inputs, runtime manifests, service supervision, and the headless turn runner.
- Manager, authenticated gateway, passive server, AG-UI, mail notifier, and the optional `houmao-cccc` integration. Preserve the existing public control entrypoints and CCCC delivery selection.
- Reference documentation, runtime and integration tests, and managed launch fixtures. The Hermes executable is supplied by the operator in the selected execution context.
