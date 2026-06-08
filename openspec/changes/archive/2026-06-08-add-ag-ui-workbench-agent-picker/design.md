## Context

The AG-UI workbench app already provides a Dockview shell, a pinned operator panel, independently configurable agent panes, a direct AG-UI client, local storage for layout and target metadata, and a Vite development proxy that allows loopback targets by default. Each pane currently has a manual target form with label, AG-UI URL, and thread ID.

The passive server already exposes `GET /houmao/agents` for discovered running agents and `GET /houmao/agents/{agent_ref}/gateway` for live gateway status. The listing includes enough metadata to show agent identity, tool, backend, session root, gateway presence, mailbox presence, and lease information. The gateway status response includes `gateway_host` and `gateway_port` when a live gateway is attached. This change uses those existing endpoints instead of adding passive-server AG-UI forwarding routes.

The intended tester is a Houmao developer running the workbench locally with Bun-global Playwright available. The tester may be validating local agents, forwarded remote gateways, or a passive server that is not on localhost.

## Goals / Non-Goals

**Goals:**

- Let testers configure a passive-server base URL and refresh the list of currently discovered Houmao agents.
- Let testers retarget an existing operator or agent pane from the discovered-agent list.
- Let testers open a new docked agent pane from the discovered-agent list.
- Keep explicit AG-UI gateway URL entry available and easy to edit.
- Reuse the existing local proxy policy for discovery, gateway-status, and AG-UI calls.
- Preserve GUI lifecycle boundaries: picker selection, retargeting, and pane creation attach to agents but do not start, stop, restart, interrupt, or shut down them.
- Add deterministic Playwright coverage with fake passive-server and AG-UI endpoints.

**Non-Goals:**

- Do not implement passive-server AG-UI proxy routes such as `/houmao/agents/{agent_ref}/ag-ui`.
- Do not add agent launch, stop, restart, interrupt, or registry cleanup controls to the GUI.
- Do not add custom authentication headers or credential storage in this change.
- Do not persist discovered-agent list responses, gateway-status payloads, stream events, prompt text, mailbox content, memory content, or raw terminal content.
- Do not add the GUI to the PyPI package.

## Decisions

### Use passive-server discovery as the picker source

The workbench will add a small discovery client that fetches `GET /houmao/agents` from a configured passive-server base URL and normalizes the returned summaries into rows for an `AgentPicker` component.

Rationale: the passive server already owns registry scanning, tmux liveness filtering, and agent-name resolution. Reusing it keeps the GUI from duplicating registry logic.

Alternative considered: inspect the live registry directly from the browser or from a workbench-side helper. That would require filesystem or tmux access from the GUI and would bypass the already-specified passive-server contract.

### Resolve selected agents through gateway status, then build a direct AG-UI base URL

When a tester selects an agent that reports `has_gateway`, the workbench will call `GET /houmao/agents/{agent_ref}/gateway`, read `gateway_host` and `gateway_port`, and build `http://{host}:{port}/v1/ag-ui`. If the gateway host is a wildcard address such as `0.0.0.0`, the workbench will derive a browser target using the passive-server hostname. If gateway status is unavailable, missing host or port, or rejected by proxy policy, the row remains visible with an unresolved or disallowed state and the manual URL field remains the fallback.

Rationale: direct per-agent AG-UI routes already exist on the gateway. This approach avoids adding backend routes only to support the first picker milestone.

Alternative considered: prefer passive-server AG-UI proxy routes. That would be cleaner for remote passive servers because the browser would only need to reach the passive server. Those routes are not part of the current backend contract, so this change defers them.

### Provide one picker component with invocation context

The UI will expose the same picker in two contexts. From a pane target form, the picker defaults to retargeting that pane, including the pinned operator panel. From the toolbar, the picker defaults to opening a new docked agent pane, with an explicit control to choose an existing pane when retargeting is desired. Double-clicking a resolved agent row executes the default action for the current context. Row actions remain available for testers who prefer explicit commands.

Rationale: pane-local selection makes "change this pane's agent" direct, while toolbar selection supports "open a pane for this agent" without requiring an empty pane first.

Alternative considered: only add a global agent list. That would make existing-pane retargeting ambiguous unless the tester separately selected an active pane.

### Retargeting detaches the GUI stream and clears pane protocol state

When a pane is retargeted, the workbench will abort any active browser stream, call AG-UI detach when a connection ID is known, clear capabilities, raw event timeline, reduced transcript, state snapshot, activity records, tool calls, errors, and run status, then apply the selected target metadata. The Dockview panel ID, position, and tab group stay unchanged.

Rationale: a retargeted pane should not mix protocol events from two agents. Detaching is GUI bookkeeping only and follows the current AG-UI lifecycle boundary.

Alternative considered: preserve old transcript while changing target. That risks misleading tests because old agent evidence would remain visible after the pane points at a new agent.

### Store only discovery configuration and selected-target metadata

The storage model will persist the passive-server base URL and selected target metadata, including source type, agent ID, agent name, passive-server base URL, derived AG-UI URL, label, and thread ID. It will not persist agent-list responses, gateway-status payloads, or stream data. Manual edits to the AG-UI URL switch the target source to manual while preserving the typed URL.

Rationale: the workbench needs to restore useful layout and target choices after reload, but discovery rows and protocol streams can contain stale or sensitive data.

Alternative considered: cache the last discovered list for offline display. That would make stale agents look available and does not help the main test workflow.

### Use the existing Vite proxy boundary for passive-server calls

The workbench discovery client will request passive-server and gateway-status URLs through the same proxy prefix used for AG-UI calls. The proxy can keep its current target query shape while accepting non-AG-UI paths as long as the target URL passes protocol and host policy checks.

Rationale: testers should get one consistent policy for browser-to-Houmao requests. This also keeps remote targets explicit through the existing allowlist environment variable.

Alternative considered: call the passive server directly from the browser. That would require CORS configuration on the passive server and split error handling between proxied AG-UI calls and direct discovery calls.

## Risks / Trade-offs

- Remote loopback ambiguity: a remote passive server may report a gateway at `127.0.0.1`, which is not reachable from the tester's browser unless forwarded. Mitigation: show the derived URL, keep it editable, and document manual gateway entry for remote or forwarded setups.
- Stale discovery rows: a listed agent may expire or lose its gateway between refresh and selection. Mitigation: resolve gateway status on selection and surface 404, 409, and 502 responses directly in the picker.
- Proxy exposure: adding discovery calls increases the set of proxied URLs. Mitigation: keep the existing HTTP/HTTPS and host allowlist checks and do not log or persist request bodies.
- Retarget race: an active stream may still emit after the user selects another agent. Mitigation: abort the active stream before updating target state and ignore events from aborted controllers.
- Visual crowding: toolbar controls, pane target forms, and the picker can compete for space. Mitigation: use icon buttons with tooltips for picker actions and keep the picker as a drawer or modal rather than expanding every pane by default.

## Migration Plan

Add the picker as an incremental workbench feature. Existing saved panes with manual targets remain valid because `TargetConfig` keeps `label`, `url`, and `threadId`; new source metadata is optional and sanitized on load. The default passive-server URL can be empty or a loopback default without forcing discovery.

Rollback is removing the new discovery client, picker component, storage fields, tests, and docs. Existing manual target entry remains the compatibility path.

## Open Questions

- Should a future milestone add passive-server AG-UI proxy routes so remote testers can target `/houmao/agents/{agent_ref}/ag-ui` through one passive-server origin?
- Should target rows support user-supplied auth headers once non-local passive servers become common?
- Should the picker eventually include lifecycle commands, or should those remain in `houmao-mgr` and passive-server APIs outside this AG-UI workbench?
