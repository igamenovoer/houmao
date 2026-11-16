# Proposal

## Why

DSH needs the same interactive agent behavior Houmao provides for other coding tools, with a browser as its native human interface. A human and Houmao must control one live Web Host session while sharing its history, progress, and execution state.

## What Changes

- Add backend `dsh_web`. Selecting DSH's existing `tui`/interactive posture launches a Houmao-owned Web Host, while headless selection continues using `dsh_acp`. This first release rejects adoption of any externally launched Web Host, including a compatible local host.
- Separate launch posture, native human surface, and supervisory terminal metadata. A DSH browser URL and native session identify the interactive surface; a tmux log pane does not become a TUI parser target.
- Implement structured Web Host control and observation of the same session used by the human browser, with independent API connection credentials and browser-owned human questions in `as_is` mode.
- Extend the packaged DSH companion with authenticated, session-bound managed control. Check live host/agent incarnations and admission atomically at the native handoff, without automatically restoring cold sessions for ordinary messages.
- Map shared native activity, pending input, permission waits, terminal outcomes, and human-initiated work into Houmao's status, detail, history, events, and usage contracts.
- Preserve immediate ordinary-message refusal and failure after body replacement. Explicit operator admission policies retain their documented meanings; native browser queues remain visible and are never mistaken for Houmao delivery retries.
- Qualify simultaneous browser/API interaction, restart, interrupted or uncertain delivery, and native usage through reproducible fixtures and browser tests.

## Capabilities

### New Capabilities

- `dsh-web-control`: Runtime-owned Web Host lifecycle, mixed human/programmatic session control, authenticated native admission, and shared-session outcome observation.

### Modified Capabilities

- `brain-launch-runtime`: Resolve DSH interactive posture to `dsh_web` and publish a Web surface with independently supervised lifecycle.
- `agent-gateway`: Add native Web readiness/control and surface-aware status while preserving immediate plugin-event and explicit operator admission contracts.
- `agent-usage-records`: Account for managed and human-initiated DSH Web work without duplicate charges or invented prompt ownership.
- `managed-agent-detailed-state`: Expose structured Web detail alongside terminal TUI and headless variants.
- `passive-server-tui-observation`: Select terminal observers by native surface and route DSH Web inspection through structured observation.
- `test-agent-launch-fixtures`: Add DSH's `tui`-as-Web lane and browser/API coexistence qualification to the existing generic fixture cases.

## Impact

Implementation extends the runtime, discovery/registry projections, gateway, manager, passive-server models, DSH assets, qualification tools, and docs established by change 01. DSH remains an external executable; no browser automation is needed for production control. Playwright is used to qualify the actual human interface in CI and live smoke workflows.

**BREAKING:** Interactive launch posture no longer implies a terminal presentation surface. State and capability consumers must branch on the declared native surface, and typed state/detail models gain a Web variant. Terminal capture, parser state, and raw keystrokes are unsupported for a Web surface. Existing terminal providers retain their established behavior.

This is change **02** and requires [dsh-01-add-acp-headless-backend](../dsh-01-add-acp-headless-backend/proposal.md) to be implemented, validated, and synchronized before application. Reuse its pinned DSH revision, configuration, native prompt, and accounting adapter. Remote/public Web deployment, adoption of externally launched Web Hosts, headless-to-Web live handoff, a mandatory LLM provider, and coordinated live refresh (#82) are outside this change. Reconnection and gateway attachment to a verified Houmao-owned host remain supported. Complete the two-change #74 scope only after both acceptance maps pass.
