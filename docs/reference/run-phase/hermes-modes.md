# Managed Hermes

Houmao resolves `hermes` on PATH in the selected execution context. The supported modes are `service`, `tui`, and `headless`. A launch without a mode selects `service`. Each agent gets a private Hermes home, configured workspace, and managed conversation. The launch profile selects the model and base URL for its Chat Completions route. The selected credential bundle supplies `HERMES_MANAGED_API_KEY`.

## Daemon and Home

The agent's recorded Hermes launch home defines daemon ownership. Houmao starts a daemon when the home has none, or silently adopts the existing daemon regardless of who started it. Independent use of the managed home has undefined behavior. A daemon serving the managed home as a secondary profile belongs to its own launch home.

Houmao checks the current process identity before managing it and keeps the loopback endpoint and one-use native tickets private. After a replacement starts in the same home, Houmao reconciles existing requests against their native admissions before handling new work. Detaching the Houmao gateway leaves daemon work running. Managed stop waits for the exact daemon to exit.

## Service

Service mode runs `hermes acp` over private stdio. The persistent client negotiates ACP and binds the selected logical conversation before publishing readiness. History replay during binding stays out of the current prompt's results. The unattended adapter selects an advertised one-time rejection when Hermes requests approval. An unsupported interaction receives a refusal.

Service interruption addresses the current ACP request. The matching result determines whether it completed or was cancelled. Loss of the ACP connection can leave work executing in the daemon. The owner retains the uncertain outcome and exact relaunch verifies the saved conversation. Stop closes the client and stops the daemon launched for the managed home.

## Terminal

TUI mode creates or resolves the managed conversation before opening Hermes Ink in the tmux pane. An `unattended` launch skips Hermes setup prompts. Attach to the pane for direct interaction. Houmao continues to address the saved conversation if the operator switches Ink to a different conversation. Closing Ink leaves the daemon available to finish admitted work.

Use `houmao-mgr agents single --agent-id <id> state` or passive `/houmao/agents/<id>/state/detail` to inspect native readiness and the terminal attachment. An unavailable native connection makes prompt readiness unavailable. Tracker history, parser controls, automated key delivery, and prompt-time session selectors are unsupported for Hermes TUI.

Houmao refuses a new managed prompt if the selected conversation is already busy. If human input starts after the native idle check, Hermes can accept the managed prompt into its queue. The receipt confirms acceptance. The matching admission reports execution and completion as they happen. An interrupt addresses that admission specifically.

## Headless

Headless uses one finite client process per turn. Houmao verifies the selected session and workspace, passes the full logical ID to the stock CLI, and supplies the literal prompt through private stdin.

```text
hermes chat --oneshot --query-file - --format stream-json --resume <native-id>
```

The native CLI tries an ID lookup and can try a title if that lookup misses. Houmao uses the recorded native ID to request continuation. A result identifying a different logical session leaves settlement uncertain.

Authorized artifact readers can inspect the separately captured stdout and stderr. Managed events come from matching native evidence. The final result supplies the complete assistant text after a replay gap. Usage stays unknown when the CLI cannot attribute it to that turn.

The client can exit while the daemon still owns accepted work. An unresolved exit leaves the active slot reserved through passive-server restart. When recovery finds a verified result, Houmao saves the continuation before admitting another turn. Native interruption requires an attributable admission. The stock CLI keeps the admission ID internally and omits it from JSONL, so Houmao refuses the interrupt.
