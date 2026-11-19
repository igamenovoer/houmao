# Stock Browser Admission Verification

This probe established the stock queue behavior before the user accepted the [check-and-send policy](check-and-send.md).

Playwright opened the stock Kimi Code `2.6.0` Web UI in a fresh Chromium context. The native host used the explicit `self-hosted` case and `Qwen/Qwen3.8-27B-FP8` over OpenAI Chat. Fixture `self-hosted-kimi-headless-raw-ae5de1a4ab09` supplied the isolated Kimi home, workspace, and selected model environment. The probe invoked `kimi web --no-open --host 127.0.0.1` directly on a fixture-owned port.

The harness verified that the child process owned the loopback listener before authenticating. It loaded the owner-private `server.token` only in the test process and disposable browser context. Native startup output stayed in the external fixture. The browser closed and the native child stopped with exit status `0`.

## Native Result

The probe seeded session `session_35fc9719-5c62-405a-a382-8465e39e3d45` with one short Qwen prompt so that the browser listed the conversation. It then selected that conversation and submitted a longer prompt through the native composer. The native POST returned `running`, and the prompt list showed the same active ID. While that browser turn was active, an independent authenticated stock API request sent a distinct text prompt. The stock POST returned `queued`, and the native list showed the same browser prompt active with the independent prompt in its queue.

| Input | Native Prompt | Journal Turn | Evidence |
|---|---|---|---|
| Browser composer | `msg_772b0fa083e66d9222e06fef0cec655c` | `1` | Running receipt, attributable native completion, and one per-turn usage record |
| Concurrent stock API prompt | `msg_01M7SD1PRXVDS7BKHNZRDDGAWZ` | `2` | Queued receipt and queue presence, later native completion, and one per-turn usage record |

The browser displayed the second prompt's requested reply, `KIMIWEB07QUEUED`, after the browser turn finished and the native queue drained. Both native journal inputs report `origin.kind=user`. The probe distinguishes them using the browser and API receipts. A native `user` origin alone cannot identify which client submitted a prompt.

This run establishes that a Houmao readiness read followed by the stock prompt POST can queue work. The positive managed browser, gateway, mail, and plugin cases still require a provider boundary that compares readiness and commits input atomically.
