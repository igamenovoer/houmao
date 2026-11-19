# DSH Headless Fixture Verification

Raw and managed fixture preparation select `dsh_headless` with an explicit model and an isolated private home. The raw fixture executes the pinned DSH binary once per prompt, with the outer `--patch` options before the profile's `--json` option. Placing a launcher patch after `--json` produced `unknown option '--patch'` in the installed build. The initial native stdout `session` event supplies the exact continuation ID. The next worker uses that ID through `--session-id`, keeps the original workspace, and receives the task through stdin. The raw fixture registers the selected role as a literal system prompt section. Its plugin supplies no managed handoff receipt.

## Automated Checks

| Command | Result |
| --- | --- |
| `pixi run pytest -q tests/unit/agents/test_dsh_fixture_tools.py tests/unit/agents/test_agent_fixture_tools.py --tb=short` | 99 passed. Compared the exact selected model, provider, argument shape, and private auth inputs for self-hosted Qwen and controlled cloud configurations. A managed DSH fixture counts usage only for the operation ID returned by its own gateway prompt. |
| `pixi run pytest -q tests/integration/agents/dsh/test_fixture_headless.py --tb=short` | 4 passed with the explicit DSH `0.2.2-rc.3` executable. Both controlled routes completed and resumed the same native conversation in two separate workers on the raw and manager surfaces. Managed handoff verified distinct worker process identities and exact native session IDs. The endpoint-only route sent the public placeholder authorization value. The controlled cloud route sent synthetic selected credentials. |
| Scoped Ruff check and `git diff --check` | Passed. |

The shipped profile initially sent an extra provider request to generate a session title. Shared headless preparation now disables the background title generator, as Web preparation already does. Both controlled raw routes then made exactly one provider request per fixture prompt. No paid cloud run was made.

## Live Raw Self-Hosted Qwen 3.8

The maintained `scripts/qualification/dsh/qualify.py` runner used DSH `0.2.2-rc.3`, source reference `39163dd30f703a79079e2d2446545cff3c453738`, and `Qwen/Qwen3.8-27B-FP8` on the explicitly selected pi-ai Chat Completions endpoint. The endpoint accepted DSH's public placeholder, so the run required no API key. Preparation and all raw artifacts stayed under external private directories.

The shell tool wrote the expected file. A new worker continued the same session and returned native `final.reason.kind=completed`. A separate worker interrupted after a native `turn_start` exited with code `130`. Fixture metadata recorded that as `interrupted` with `worker_exit` evidence. Both isolated native homes stopped through owned cleanup. Raw capture exercises no managed usage route, so the report lists that check as `not_run` and the lane as `partial`.

## Live Manager and Authenticated Gateway

The same runner selected `--surface manager` and the same DSH build, model, and endpoint. It passed the shell tool file oracle, exact continuation, managed gateway ledger history for the two completed turns, interruption after the companion recorded a native claim, and two isolated homes. The gateway calls used signed owner-self requests. The original run recorded `completed`, `completed`, and `interrupted`. Both agents stopped through owned cleanup on their private tmux sockets.

A separate live fixture submitted a signed gateway prompt and waited for the finalized usage row matching its queued operation ID. It detached the gateway, stopped the agent, and relaunched with `--chat-session-mode exact` and the saved native session ID. The relaunch retained the Houmao agent ID, switched owner generation, and staged native adoption for the next explicit prompt. A reattached gateway accepted a second signed prompt under a different operation ID. Its completed usage row confirmed the same native session and ledger stream. The earlier row remained unchanged and retained its original generation. Cleanup stopped the reattached listener and owned agent on the verified private socket.
