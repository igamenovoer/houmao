# Managed Hermes

Managed Hermes uses a prepared installation in the selected execution context. The supported modes are `service`, `tui`, and `headless`. A launch without a mode selects `service`. Each agent gets a private named-profile home, configured workspace, and managed conversation. The launch profile selects the model and base URL for its Chat Completions route. The selected credential bundle supplies `HERMES_MANAGED_API_KEY`. [Prepare the Owner Installation](hermes-owner-setup.md)

## Reasoning Effort

Set `--reasoning-level` on a Hermes launch or profile to choose an effort for the agent's custom Chat Completions route. Houmao applies the same launch presets in all three modes.

| Level | 0 | 1 | 2 | 3 | 4 | 5 | 6 and higher |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Effort | `none` | `minimal` | `low` | `medium` | `high` | `xhigh` | `max` |

To set an exact native default, supply `tool_params.reasoning_effort` in the launch profile or `reasoning_effort` in the setup's `tool-params.yaml`. Use one of the labels in the table. A resolved numeric level takes precedence over that default. For example, the following profile defaults to `low`, and the one-off launch selects `xhigh`.

```bash
houmao-mgr project profile set --name hermes-dev --tool-params '{"reasoning_effort":"low"}'
houmao-mgr project agents launch --profile hermes-dev --reasoning-level 5
```

Houmao writes the selected value to `agent.reasoning_effort` in the private `$HERMES_HOME/config.yaml` and records its source in launch provenance. If both inputs are absent, Hermes uses its native default. Level `0` or the exact label `none` explicitly requests disabled reasoning.

## Startup Permissions

Unattended Hermes uses the native approval mode `off` and selects `approve` for finite query and unattended interactions. Houmao applies these settings to its private home and verifies the effective settings on the current daemon before accepting managed prompts. Native hard denials and execution-owner limits still apply. Select `as_is` to use Hermes's native approval behavior and custom settings.

## Shared Gateway and Profile Lifecycle

The execution owner runs one shared Hermes gateway from its prepared root. Each worker has its own profile, credentials, session store, clients, and workspace. The project's `runtime/homes/<home-id>` entry links to the worker's canonical `<hermes-root>/profiles/<profile-name>` directory. Houmao verifies the host process and the selected profile's authority before requesting a native ticket. Two profiles on one host can have different authority epochs.

Stopping a worker closes its managed clients, parks the profile, and verifies that Hermes released the profile reservation. A profile with unconfirmed release stays parked and retains its evidence. The shared host stays available for other workers and future launches. An exact relaunch verifies the saved conversation in the retained profile. Following a host replacement, Houmao reconciles existing admissions against that profile and session before accepting new work. Detaching the Houmao gateway leaves native work running.

Recorded standalone agents retain their inspection, stop, and cleanup authority. Start a fresh managed worker to adopt the named-profile layout.

Local shell tools launched by a current managed Hermes conversation can use `houmao-mgr agents self` for identity, state, and mailbox discovery, including when Ink is detached. The profile's native session hook gives each tool a short-lived proof bound to its served profile, conversation, and managed generation. Houmao verifies that origin and the live runtime before selecting the self signer. Use the command from the recorded conversation's tool. An operator shell, remote tool runner, or tool from a different conversation lacks this proof. A Headless turn that switches conversations must finish before tools in the new conversation can use managed self. A recorded standalone Service or TUI generation uses its existing daemon ownership evidence.

`houmao-mgr agents self mail resolve-live` discovers the current mailbox and gateway binding. Mail operations through a live gateway use the current managed-self key and grants. Parking a profile or replacing its authority invalidates outstanding proofs and prevents pending self-authorized effects from using the old binding. Commands that control a terminal still require the owning terminal surface.

Operator gateway requests use the configured admin signer when present. Without one, the gateway applies its policy for unsigned callers. Managed-self signing is reserved for tools with verified profile and session origin.

## Service

Service mode runs `hermes acp` over private stdio. The persistent client negotiates ACP and binds the selected logical conversation before publishing readiness. History replay during binding stays out of the current prompt's results. Unattended service verifies the native `dont_ask` mode for the bound conversation. If a currently authorized prompt receives a supported tool permission request for that session, the client can grant the advertised one-time option. Unsupported, stale, or other interactions fail closed.

Service interruption addresses the current ACP request. The matching result determines whether it completed or was cancelled. Loss of the ACP connection can leave work executing in the shared host. The owner retains the uncertain outcome and exact relaunch verifies the saved conversation. Stop closes the client's ACP connection and retires that worker's native profile authority.

## Terminal

TUI mode creates or resolves the managed conversation before opening Hermes Ink in the tmux pane. An `unattended` launch skips Hermes setup prompts. Attach to the pane for direct interaction. Houmao continues to address the saved conversation if the operator switches Ink to a different conversation. Closing Ink leaves the daemon available to finish admitted work.

Use `houmao-mgr agents single --agent-id <id> state` or passive `/houmao/agents/<id>/state/detail` to inspect native readiness and the terminal attachment. An unavailable native connection makes prompt readiness unavailable. Tracker history, parser controls, automated key delivery, and prompt-time session selectors are unsupported for Hermes TUI.

When Hermes reports a current approval wait, the manager and passive server expose the boolean `control.approval_pending`. Gateway status exposes `observation.approval_pending`. A value of `null` means Houmao lacks verified approval state. A pending approval closes ordinary managed prompt admission until Hermes settles the interaction. This state describes the managed conversation even when Ink is detached or displaying a different conversation.

Houmao refuses a new managed prompt if the selected conversation is already busy. If human input starts after the native idle check, Hermes can accept the managed prompt into its queue. The receipt confirms acceptance. The matching admission reports execution and completion as they happen. An interrupt addresses that admission specifically.

Use `houmao-mgr agents single --agent-id <id> prompt --prompt "Your request"` to send a prompt to the saved native conversation. The manager checks that conversation's current native readiness even if Ink is closed or showing a different conversation. It reads receipts directly from Hermes, so the same command works with the Houmao gateway detached.

The manager waits within its request budget and returns the original Houmao `request_id` with `evidence_source: "tui_native"`. A verified terminal receipt reports `completed`, `failed`, or `interrupted`. If the wait ends first, `queued` confirms native queue acceptance and `handed_off` confirms that Hermes started the request. `uncertain` means the manager could not confirm native admission. An outstanding request remains in the owner slot until exact evidence settles it or an authorized lifecycle operation fences it. Delegated calls use the configured owner execution deadline.

## Headless

Headless verifies an initial conversation at managed launch and uses one finite client process per turn. Houmao verifies the selected profile, session, and workspace, passes the full logical ID to the stock CLI, and supplies the literal prompt through private stdin.

```text
hermes --profile <native-profile> chat --oneshot --query-file - --format stream-json --resume <native-id>
```

The native CLI tries an ID lookup and can try a title if that lookup misses. Houmao uses the recorded native ID to request continuation. A result identifying a different logical session leaves settlement uncertain.

Authorized artifact readers can inspect the separately captured stdout and stderr. Managed events come from matching native evidence. The final result supplies the complete assistant text after a replay gap. Usage stays unknown when the CLI cannot attribute it to that turn.

The client can exit while the daemon still owns accepted work. An unresolved exit leaves the active slot reserved through passive-server restart. When recovery finds a verified result, Houmao saves the continuation before admitting another turn. Native interruption requires an attributable admission. The stock CLI keeps the admission ID internally and omits it from JSONL, so Houmao refuses the interrupt.
