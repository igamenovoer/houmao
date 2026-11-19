# Claude and Codex Permission Qualification

## Startup Projection

The Claude checks exercised omitted unattended permissions, explicit `dontAsk` under both prompt modes, and preservation of native deny rules and credentials. The default home and CLI selected `bypassPermissions` and seeded the dangerous-mode startup notice. The restricted-mode checks saw `permissions.defaultMode = "dontAsk"` and `--permission-mode dontAsk`. Resume-control tests verified that argument reconstruction reads existing startup state without rewriting provider files. [Claude permission modes](https://code.claude.com/docs/en/permissions#permission-modes).

The Codex checks exercised the private home, final CLI config arguments, native argument aliases, model and provider settings, and native arrays of tables. A conflicting project-local config stayed intact while the generated CLI options selected the authored permission pair. The app-server subprocess peer checked fresh and exact-resume requests for the default and restricted pairs. Separate mismatch cases proved that incorrect approval and sandbox echoes prevent readiness.

```bash
pixi run pytest -q tests/unit/agents/test_launch_policy.py \
  tests/unit/agents/realm_controller/test_codex_app_server.py \
  tests/unit/agents/realm_controller/test_codex_bootstrap.py \
  -k 'claude or codex or as_is_launch_policy'
pixi run docs-build
```

The focused unit command passed 48 cases. The strict MkDocs build passed. The Claude/Codex selections in `tests/integration/agents/test_agent_fixture_launches.py` passed 16 managed and raw fixture cases with private tmux servers and cleared `TMUX` and `TMUX_PANE`. The same batch's additional proxy-env test, `test_easy_profile_env_reaches_codex_tui_tmux_session`, failed the preexisting version requirement because its executable stub reports `0.140.0` and the unattended registry requires `>=0.162.1`. A trial stub version update reached an early fixture tmux server exit. The trial fixture change was reverted.

## Live Codex Service

Two manager fixtures used installed Codex CLI `0.169.0`, `--case self-hosted`, `--mode service`, and `Qwen/Qwen3.8-27B-FP8` through the selected local Responses endpoint. Both used the fixture's isolated roots and exact tmux socket. The service owner required the native thread's effective approval and sandbox fields to agree before reporting readiness.

| Fixture | Effective Policy | Verified Outcome |
| --- | --- | --- |
| `self-hosted-codex-service-manager-74c685e9b696` | Omitted fields resolved to `never` and `danger-full-access` | Signed gateway prompts completed before and after exact relaunch. The new service incarnation retained the native thread. Scoped stop returned `stopped_owned_identity`. |
| `self-hosted-codex-service-manager-1e7371322c83` | Specialist `tool_params` explicitly selected `on-request` and `read-only` | Manifest recorded both authored values. Signed gateway prompts completed before and after exact relaunch. The replacement owner retained the native thread and authored values. Scoped stop returned `stopped_owned_identity`. |

The authored case used `project specialist set --name fixture-agent --tool-params '{"approval_policy":"on-request","sandbox_mode":"read-only"}'` after fixture preparation. Both tests used `fixture.py` for prepare, launch, prompt and stop. The manager used the fixture authority for gateway detach, exact continuation and reattachment. Private fixture captures remain under the temporary run root.
