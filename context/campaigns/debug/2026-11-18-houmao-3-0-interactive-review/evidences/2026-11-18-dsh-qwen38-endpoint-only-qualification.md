# DSH Endpoint-Only Qualification Against Qwen 3.8

On 2026-11-18, the Iteration 1 driver completed the `b1` ACP and `b2` Web arms against self-hosted SGLang. The run used the qualified `@deepseek-ai/dsh` `0.2.2-rc.3` binary and exact model `Qwen/Qwen3.8-27B-FP8`. SGLang returned HTTP 200 for the model catalog at `http://127.0.0.1:14888/v1/models`. [Iteration 1 driver](../../../../../scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py)

## Method

The driver ran from private temporary directories outside the checkout, with ambient provider variables cleared and a separate tmux socket. Each credential bundle contained only `OPENAI_BASE_URL`, and the effective provider configuration set `api_key_env: null`. A temporary loopback relay forwarded the streamed responses from the real SGLang server. It recorded the model, wire reasoning effort, message roles, and whether the authorization header matched `Bearer houmao-local-no-auth`.

## Settled Results

| Arm | Prompt | Wire `reasoning_effort` | Wire roles in order | Exact placeholder header | Signed usage |
|---|---|---|---|---|---|
| `b1` ACP | `P1`, level 0 | `none` | system, user, user | Matched | Completed, 6,683 total tokens |
| `b1` ACP | `P1`, level 1 | `low` | system, user, user, assistant, user | Matched | Completed, 6,808 total tokens |
| `b2` Web | `P1`, launch default level 0 | `none` | system, user, user, user, user | Matched | Completed, 10,574 total tokens |

The Web endpoint reported native turn settlement as `completed`. Signed usage was queried using the gateway port from the captured status because the driver did not parse the original Web launch output. The placeholder value was absent from all 24 checked credential, tool-parameter, generated-patch, and manifest files. Both generated patches selected `houmao-unattended`. All three ACP `provider-stderr.log` files had zero permission preset-mismatch errors.

## Controlled Rejection and Cleanup

The relay returned HTTP 400 with synthetic Bearer, API-key, and cookie values for one subsequent `b1` request. The CLI exited 1, showing ACP code `-32603`, HTTP 400, the test message, and three `[REDACTED]` markers. The synthetic values were absent from the operator-facing output. Signed usage finalized one failed turn with zero tokens. The immediate state snapshot still showed the preceding successful turn in `last_turn`.

Both agents stopped successfully. Teardown found zero sessions on the isolated tmux server and confirmed that the default server's session list was unchanged. The relay was stopped.
