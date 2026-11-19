# Implementation and Verification

## Environment

- Pixi development checkout based on `b95403ef`.
- Self-hosted model `Qwen/Qwen3.8-27B-FP8`, advertised context window 262,144. The configured loopback endpoint returned this exact model from `GET /v1/models`.
- Live lanes use explicit fixture inputs with inherited `TMUX` and `TMUX_PANE` cleared. The installed Kimi build reports `2.6.0`. The selected isolated DSH build reports `0.2.2-rc.3`, SHA-256 `36f86742e0c3cc1c3b2dbaa6582ee00b0c37bc4f5a190f7531b5303bf3efb6d9`.

## Decisions

- The user-selected self-hosted Qwen 3.8 model replaces the original live qualification model constraint. The fixture retains hermetic DeepSeek configuration coverage.
- The current project support matrix exposes DSH Web. DSH native headless and persistent ACP are gated by changes 03 and 04. The existing per-turn ACP implementation has no public birth route in this stage.
- Launch plans use schema 3, manifests schema 6, managed registry records schema 5, and routed execution locators schema 2.

## Automated Verification

| Check | Result |
| --- | --- |
| `openspec validate run-modes-01-introduce-managed-agent-run-modes --strict` | Passed. |
| `pixi run lint` and `pixi run typecheck` | Passed. Mypy checked 505 source files. |
| `pixi run test` | Passed 4,804 tests, with 14 skips and 10 dependency deprecation warnings. The run used eight workers and a private tmux root. |
| `pixi run docs-build` | Passed. The theme printed its MkDocs 2.0 notice. |
| Focused selector, launch policy, DSH launch, and saved-mode revival | Passed. Covered all entrypoint defaults, explicit backend conflicts, stored-profile edits after birth, and RC2 per-turn ACP rejection. |
| Owner/router/cleanup tests | Passed 109 tests. Covered invalid owner preflight, manifest/locator mismatch, and token-free Web projection. |
| Passive observation and local manager tests | Passed 381 tests. Covered registry and manifest agreement and supported synthetic gateway contracts. |
| Fixture, packaged skills, config drafts, demos, and login smoke unit tests | Passed 167 tests before the private socket fix. The private login smoke here uses synthetic credentials. |
| Controlled native DSH Web browser/API fixtures | Passed all four raw/manager protocol cases after the private socket fix. |
| Fixture isolation unit tests | Passed 104 tests after the fix. A 33-test rerun also passed after switching to an explicit `-S` for every fixture tmux operation. The tests cover a real private socket and refusal of foreign sockets. |
| Maintained project launch cases in `test_cli_shape_contract.py` | Passed both cases. The full file has the same 17 failures and five passes on the base checkout and the implementation. The failures exercise retired root-level commands and a stale overlay expectation. |

## Findings During Implementation

- The first full unit run reported 99 failures. The report exposed synthetic records that still used RC2 schemas, fixtures that changed the backend without updating the corresponding mode, and mocked routed replies that omitted the required identity. The fixes exercise the versioned contract in the affected fixtures. The ignored scratch log `tmp/run-modes-verification/01-unit.log` holds the first result.
- The initial managed fixture used a named tmux wrapper, but runtime socket capture appended an explicit default `-S` and overrode that name. The test closed its own launched identity. Dedicated live reruns require a recorded fixture socket, a matching tmux server, and scoped cleanup.
- The legacy per-turn DSH ACP fixture acceptance paths cannot qualify the new headless or service mode. Changes 03 and 04 will update the maintained native acceptance paths as the corresponding entrypoints become selectable.

## Live Verification

- Kimi `2.6.0` with `self-hosted`, `openai_chat`, and `Qwen/Qwen3.8-27B-FP8` launched through the public manager in unattended `tui` mode with `local_interactive`. JSON reported a terminal surface, the non-interactive handoff, and an attach command naming the private socket. The pane showed the assistant reply `MODETUI01`. The usage ledger recorded one completed turn. Scoped stop succeeded.
- DSH `0.2.2-rc.3` with `self-hosted`, `pi-ai/openai_chat`, and the same Qwen model launched in `web` mode with `dsh_web`. The maintained Web qualification passed API tool use, browser tool use, exact continuation, human usage, human interruption, exact host relaunch, and two isolated homes. Chromium `156.0.8078.4` selected the same native session as the manager. The browser location after sign-in contained only the safe origin. Both owned agents stopped successfully.
- Both live lanes verified that the fixture socket, the persisted tmux socket, and the socket queried from tmux matched. The first Kimi pane check assumed a bare reply line. The actual Kimi pane prefixes the assistant reply with `●`. The scoped pane capture and completed usage row verified the same turn.
- The launch and `agents global list --state all` output report the same Web `tool`, `mode`, `backend`, `native_surface.kind`, origin, and native session ID. The lifecycle reference sample uses a representative session ID.
