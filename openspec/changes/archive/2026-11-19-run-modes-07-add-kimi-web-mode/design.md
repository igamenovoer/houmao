# Design

## Native Host and Browser Handoff

Start stock Kimi Code `2.6.0` with `kimi web --no-open` on loopback under the saved execution context. Use the private native home, selected workspace, and projected model configuration. Qualify the process and listener before sending the token. Kimi prints the bearer in its startup banner even with `--no-open`, so capture or discard native startup output privately. Publish a clean origin and exact session. Browser credentials are retrieved separately through an explicit owner-local action. Use the existing execution-context routing for owner calls. [Native Web launcher](../../../extern/orphan/kimi-code/apps/kimi-code/src/cli/sub/web/run.ts).

## Managed Dispatch

The controller, gateway, ordinary plugin, and mailbox use the same owner reservation. Immediately before the native POST, verify the bound host and session, check the current native active prompt and queue, and recheck dispatch authority. Observed busy, pending work, or unavailable evidence returns a refusal before sending. Kimi's browser can send independently between the check and the POST. If the native API accepts the managed prompt as queued in that window, preserve its native prompt ID and queued result. The sender issues one POST and reconciles an ambiguous response by exact prompt identity without replay. [Native prompt routes](../../../extern/orphan/kimi-code/packages/kap-server/src/routes/prompts.ts).

Ordinary preparation sends literal text. Per-request model and other native settings overrides are outside the initial support because Kimi can change session settings before queue insertion. The owner chooses model and permission posture at launch.

## Exact Observation and Lifecycle

Read verified live state, or return unavailable for cold state without activating it. Match request evidence to the current owner generation, host, native session, and prompt. Native `user` origin can mean browser or API. Attribute it to the gateway only when the exact managed correlation matches. A target-specific abort uses the native prompt ID and waits for attributable settlement before reporting an outcome. Retain prior request evidence across gateway reattachment. Stop only the owned host. Explicit relaunch validates the saved workspace and exact native session before enabling dispatch.

## Qualification

Use Chromium to hold an actual browser turn on self-hosted `Qwen/Qwen3.8-27B-FP8`. Exercise a busy rejection before native input and record the stock queued outcome when the browser wins after the check. Verify exact turns and loss handling through public manager and authenticated gateway. Check passive observation, session resume, access-bearing data in public output, and private cleanup.
