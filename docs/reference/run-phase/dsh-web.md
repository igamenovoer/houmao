# DSH Web Compatibility

This reference tracks the interactive Web implementation in `dsh-02-add-interactive-web-backend`. DSH's interactive posture uses a browser interface under a Houmao-owned local host. Its supervisor terminal provides process/log authority; native control and observation use authenticated structured services.

## Qualified Predecessor

Change `dsh-01-add-acp-headless-backend` completed all 29 tasks and its live DeepSeek acceptance before Web implementation began. Its seven delta specs were synchronized into the main specifications. Normal validation passed all 240 main specs; strict checks identified no introduced warnings.

| Identity | Qualified Value |
| --- | --- |
| Source revision | `39163dd30f703a79079e2d2446545cff3c453738` |
| Native executable/package version | `0.2.2-rc.3` |
| Executable SHA-256 | `36f86742e0c3cc1c3b2dbaa6582ee00b0c37bc4f5a190f7531b5303bf3efb6d9` |
| DeepSeek package-code SHA-256 | `ac0a9f14c56acd12081b12702887fccc5948a07e0a9c9f27128e0d5eff6a088c` |
| Headless full unit baseline | 4,018 passed, 14 skipped |
| Final headless native regression | 17 passed in 98.46 seconds |
| Headless live provider | `deepseek-flash`, Messages, manager surface; tool completion, exact resume, usage, interruption, and two isolated homes passed |

The installed npm metadata does not attest to a source commit. These identities and conformance results qualify the tested build separately from the ACP handshake's placeholder version. [Headless acceptance](dsh-headless-acceptance.md) records the evidence and limits; the Web surface requires its own native, browser/API, accounting, and live acceptance.

## Implementation Status

Web runtime, native authentication/admission, shared-session identity, and actual browser/API coexistence have passed qualification. The [scenario acceptance map](dsh-web-acceptance.md) records all 96 delta scenarios, 84 combined native cases, 4,150 unit passes, and the seven-check real DeepSeek Web smoke. Self-hosted live qualification requires a separately selected compatible deployment/model.

## Launch and Surface Selection

DSH keeps the existing interaction posture: `headless` selects `dsh_acp`; `tui` (or a manager launch with `--no-headless`) selects `dsh_web`. A Web host uses a private DSH home, an explicit model/provider catalog, a loopback listener, and `--no-open`. Port zero requests an available listener; Houmao records the port actually bound by the host. The host's tmux session supervises its process and private logs. It does not expose a human terminal interface, parsed prompt surface, terminal timing authority, or raw-key input.

| Field or Control | Web Meaning |
| --- | --- |
| Specialist/recipe `tool: dsh` | Selects the maintained DSH tool and explicit API setup. |
| Profile `defaults.posture.headless` | `true` selects ACP; an omitted/false posture permits interactive Web. A launch `--headless` or `--no-headless` overrides this choice for that invocation. |
| Recipe `launch.prompt_mode` / profile `defaults.prompt_mode` | `unattended` is the automation default; deliberate `as_is` retains native human approval behavior. |
| Explicit model/setup metadata | Reuses DSH provider/protocol, context/output capacities, reasoning, and credential-reference validation. No ambient route is substituted. |
| `LaunchPlan.native_surface_kind` | `web`; published `native_surface` carries only verified origin and native session ID. |

After preparing a DSH specialist with its explicit setup, a reusable Web profile can use the maintained CLI:

```bash
houmao-mgr project profile create --name dsh-browser --specialist dsh-specialist --prompt-mode unattended
houmao-mgr project agents launch --profile dsh-browser --no-headless --gateway-background --workdir /selected/workdir
```

The [fixture workflow](../../../scripts/agents/test-fixtures/README.md#dsh-acp-and-web) prepares that specialist and its private model/credential inputs reproducibly. The [launch-profile reference](../../getting-started/launch-profiles.md) defines profile precedence and storage.

The first release starts Houmao-owned local hosts. A manually started DSH host cannot be adopted, even if it has a compatible companion or matching workspace. Refusal leaves that host untouched. A verified connection to an existing Houmao-owned host may reconnect or reattach a gateway while retaining the exact native session and live incarnation. Read-only status, detail, and history do not start a stopped host or activate a cold native agent.

Public Web surface metadata contains `kind: web`, a token-free `origin`, and the exact `native_session_id`. Process supervision metadata remains separate. A logical runtime identity can survive explicit relaunch, but the host and agent incarnation change. Stale credentials or incarnation tokens cannot authorize the replacement.

Use the recorded managed ID for `houmao-mgr agents single --agent-id ID state` and `gateway status`. Reconnecting or reattaching through that saved owned authority verifies the existing host binding. A token, origin, native session ID, or terminal `join` operation does not grant launch ownership of a manually started Web host.

## Browser Entry and Exact Session Selection

Use the fixture's private local connection mechanism to obtain the native browser sign-in URL. Keep that URL in the external private run root and open it only in the intended browser. The pinned host exchanges the root `/?token=...` URL for an HttpOnly browser cookie and redirects to the clean root URL. Do not paste the sign-in URL, token, cookie, startup log, or browser storage into reports, shell history, issue comments, screenshots, or shared manifests.

The stock client opens at the origin and restores its own saved selection. It has no qualified `?sessionId=` deep-link contract. Select the exact native session from the sidebar, then verify it against the published native session identity before submitting browser work. Browser qualification clicks the native sidebar row keyed by that identity and verifies its selected state. Navigation to a different browser session does not retarget Houmao's programmatic binding.

Houmao obtains a separate API Peer using `/connect` with `interactions=none`, then owns that peer's WebSocket and cookie lifecycle. It never reuses the browser cookie. Closing or revoking the API connection must leave the browser usable; a browser answering a native question must not be competed with by the API observer. A new API connection can inspect state and receipts before the operator chooses another mutation. The [native control reference](dsh-web-control.md) defines the versioned client and receipt contract.

## Admission and Shared Activity

Native DSH normally accepts browser queueing and steering. Houmao adds conditional admission at the final native handoff, after asynchronous preparation. A fresh observation is useful evidence; the synchronous native check remains the authority. An ordinary `ready_only` delivery requires the intended live host and agent, a valid caller lifetime and deadline, true idle execution with no maintenance, an empty inbox, and no blocked interaction. Human input arriving during preparation can therefore refuse the programmatic attempt without leaving delayed work behind.

| Policy | Intended Use | Native Handoff |
| --- | --- | --- |
| `ready_only` | Ordinary prompts, mail reminders, and plugin delivery | Requires true idle, no maintenance, empty inbox, and no blocked interaction. |
| `if_no_pending` | Explicit operator queueing | May insert while busy when the inbox is empty and unblocked. |
| `always` | Explicit operator queueing or steering | Bypasses busy/inbox checks while preserving ownership, authentication, availability, deadline, lifetime, and incarnation checks. |

An insertion acknowledgement proves that native input was admitted. It does not prove a turn started or finished. Input and turn receipts correlate the operation with native claims; shared state separately shows browser-origin turns, queued input, interaction waits, maintenance, and terminal outcomes. Unsubmitted browser drafts remain local and never become fabricated native pending-input or typing state.

Automation defaults to `unattended`. Select `as_is` deliberately for human approval/question qualification; that posture preserves native approval and sandbox behavior. The API remains `interactions=none` in either posture, leaving the browser to answer human interactions. A blocked question remains visible and refuses ordinary programmatic delivery.

## Interruption, Failure, and Recovery

An explicit operator interruption targets the bound live incarnation and native turn. Attempt cancellation targets the turn claimed by that attempt. A late cancellation must not interrupt a later human turn. Visible queued input remains part of native state and requires its own deliberate operator decision.

After a lost admission response, use read-only receipt lookup for the original operation ID. A receipt contains metadata, not executable prompt text. Reconnection never resubmits the prompt. Host death or agent replacement can leave the attempt failed or uncertain; neither condition authorizes an automatic resend or cold activation.

Explicit relaunch reconciles provably abandoned, unclaimed Houmao input before activating the restored session. It preserves human input, explicitly queued operator input, and claimed history. Recovery refuses when it cannot establish that boundary safely. Inspect state/history and retained private evidence, then choose an explicit lifecycle action.

## Observation and Accounting

Web detail and bounded history come from native state, history, and follow services. Terminal capture and production DOM automation do not provide Web authority. An unreachable or stale native source is unavailable even while the supervising tmux process remains alive. Sequence gaps require a new baseline; repeated events do not become new activity. The [integration reference](dsh-web-integrations.md) describes gateway, plugin, mail, and passive-server projections.

The DSH journal collector includes verified human-origin turns. Managed input claims determine attribution; waiting for a programmatic result does not own later human work. Mixed managed/human input in one native turn charges that turn once, while a later human turn remains separate. Journal requests supply the actual provider/model and disjoint usage buckets, including a model changed in the browser. Reconnect, gateway restart, and explicit host relaunch preserve accounting cutoffs and immutable finalized records.

## Qualification Boundaries

Controlled browser/API qualification uses the real identified Web executable, native UI, synthetic credentials, and a loopback model endpoint. Playwright runs through the existing Bun toolchain with headless Chromium; no desktop display or paid account is required. Tests must clear inherited `TMUX` and `TMUX_PANE` and use an explicit private tmux socket or label for every command and cleanup.

The maintained fixture helper reuses the explicit `cloud-api` and `self-hosted` descriptors, model capacities, reasoning metadata, and external credential/run roots. A fresh cloud host needs the selected API route and metadata; it does not need a local model or native auth JSON. Live DeepSeek and self-hosted results are recorded separately. A missing configured self-hosted deployment is `not_run`, and passing headless ACP does not qualify Web.
