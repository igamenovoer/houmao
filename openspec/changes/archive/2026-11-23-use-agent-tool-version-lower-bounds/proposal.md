# Proposal

## Why

A Kimi Code update from 2.6.0 to 2.7.2 blocked managed Web launch before Houmao could check the native API. Exact executable pins create the same risk for Kimi ACP and Codex app-server when operators upgrade their tools. [Houmao issue #90](https://github.com/igamenovoer/houmao/issues/90)

## What Changes

- Use inclusive minimum versions for maintained DSH, Kimi Code, Claude Code, and Codex launch requirements. Keep the current baseline for each backend and admit later releases through the same version check.
- Apply the same backend minimum at manager preflight, unattended strategy selection, and native startup wherever those paths already check executable compatibility.
- Verify native protocol, capabilities, and ownership before publishing readiness. Report the specific compatibility check that failed and record the actual tool version where startup publishes build information.
- Document the minimums and record separately which versions supplied test and qualification evidence. Cover below-minimum, baseline, and newer versions in regression tests.

## Capabilities

### New Capabilities

### Modified Capabilities

- `versioned-launch-policy-registry` defines inclusive version minimums for packaged strategies for the four tools.
- `brain-launch-runtime` applies native launch minimums independently of unattended policy and distinguishes Codex service version and capability failures.
- `claude-cli-noninteractive-startup` defines Claude's existing unattended requirement as an open-ended minimum aligned with TUI tracking.
- `kimi-web-control` admits builds at or above the Web minimum and verifies native readiness.
- `kimi-acp-service-control` admits builds at or above the ACP minimum and verifies the actual peer and its capabilities.
- `codex-app-server-control` admits builds at or above the service minimum and verifies the actual peer and its capabilities.
- `docs-launch-policy-reference` documents the backend minimums and how Houmao verifies compatibility after version admission.

## Impact

The change affects packaged launch-policy data, manager preflight and launch planning, Kimi Web startup, and the Kimi ACP and Codex app-server handshakes. It also affects startup diagnostics, build metadata, regression tests, and operator references. Usage accounting and native refresh continue to use their own evidence requirements.
