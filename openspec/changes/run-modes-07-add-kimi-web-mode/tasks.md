# Tasks

## 1. Qualify Conditional Native Submission

- [ ] 1.1 Inspect the selected Kimi build for a supported conditional prompt operation or supported in-process integration at the native commit boundary. Record build and interface evidence. On the stock unconditional route, prove busy submission can enqueue and verify the pair reports unsupported.
- [ ] 1.2 Implement and version-gate the conditional integration across host/session identity, dispatch revocation, cold activation, preparation, overrides, and enqueue. Race it directly against native human input and verify a losing request leaves neither a model change, pending input, nor a later provider call. Keep the positive qualification pending until a supported integration exists.
- [ ] 1.3 Document required native capabilities and the public unsupported outcome for an incompatible build. Verify selection fails before advertising a supported Kimi Web surface or taking over an existing agent.

## 2. Bind Browser and Machine Clients to One Host

- [ ] 2.1 Add the Kimi Web launch policy, private home and loopback host supervision with `kimi web --no-open`. Verify host/process/session binding and independent browser and machine authentication before accepting work. Exercise a wrong listener or stale owner without sending a native token.
- [ ] 2.2 Protect native startup output, authorize explicit browser opening and publish a sanitized handoff for local and routed execution. Inspect startup failure, tmux diagnostics, discovery, passive output, and gateway responses for raw bearer values and token fragments.
- [ ] 2.3 Project native session/prompt IDs, origin, queue status, and terminal evidence into shared status and AG-UI. Test an untracked browser turn and cold-session inspection, and verify status cannot wake a native session or complete an unrelated run.
- [ ] 2.4 Implement targeted abort, gateway reattachment, owner stop, and exact-session relaunch. Test a stale prompt handle after replacement, independent browser logout/disconnect, and a lost submission response without resending the prompt. Document the operator handoff and recovery flow.

## 3. Prove Mixed Browser and Gateway Control

- [ ] 3.1 Run a real browser with Playwright against the qualified native host. Pause ordinary gateway, plugin, and mail submissions before native admission while the browser starts a turn. Verify conflict, unchanged native settings, an empty managed queue, and no late provider call after idle.
- [ ] 3.2 Exercise successful browser and gateway turns in the same conversation through the public manager, gateway and passive APIs. Record exact build, case, model, host/session/prompt identities, and bounded attribution or unknown usage.
- [ ] 3.3 Run relevant Pixi and browser integration suites with isolated tmux and private fixture credentials. Publish this pair as maintained only when the real native admission, recovery, and mixed-control cases pass.
