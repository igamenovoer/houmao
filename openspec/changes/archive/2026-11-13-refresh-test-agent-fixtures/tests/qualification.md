# Fixture Qualification

Qualification date: 2026-11-13. This report contains selected configuration and numeric/public outcomes. Credentials, native homes, raw client captures, and private project catalogs remain outside the checkout under the XDG test-fixture run root.

## DeepSeek Live Runs

All runs selected `cloud-api`, model `deepseek-flash`, and an explicit context field of 1048576. Claude used Anthropic Messages at the configured Anthropic root; Codex used Responses and Kimi used Chat Completions at the configured OpenAI root. Codex selected reasoning effort `low`. Kimi selected `reasoning_content`, with `tool_use` capabilities. These short-prompt checks verify projection and execution, rather than maximum-context capacity.

| Client | Installed Version | Raw Headless Capture | Managed Headless | Managed Unattended TUI |
| --- | --- | --- | --- | --- |
| Claude Code | 2.1.323 | Fresh and exact-session resumed prompts, both exit 0 | Two completed turns in the same provider session | Direct literal input and Enter, one completed turn |
| Codex | 0.167.2 | Fresh and exact-session resumed prompts, both exit 0 | Two completed turns in the same provider session | Direct literal input and Enter, one completed turn |
| Kimi Code | 2.6.0 | Fresh and exact-session resumed prompts, both exit 0 | Two completed turns in the same provider session | Direct literal input and Enter, one completed turn |

Claude and Codex native model fields reported `deepseek-flash`. Kimi native records reported its `__kimi_env_model__` alias; the selected private `KIMI_MODEL_NAME` was `deepseek-flash`. API preparation required no imported auth JSON. Each lane used a fresh private run and home.

The public gateway usage records had the following provider-reported input/output buckets. Cached input remains a separate bucket where the provider declares disjoint token semantics. These values do not assert provider billing prices or private-subagent inclusion.

| Client | Headless Fresh Input/Output | Headless Resumed Input/Output | TUI Input/Output |
| --- | --- | --- | --- |
| Claude Code | 21795 / 10 | 196 / 12 | 24844 / 8 |
| Codex | 10596 / 17 | 10635 / 11 | 12778 / 84 |
| Kimi Code | 13025 / 10 | 225 / 12 | 14803 / 8 |

Private artifact locators, relative to `${XDG_STATE_HOME:-~/.local/state}/houmao/test-fixtures/runs/`:

| Client | Raw | Managed Headless | Managed TUI |
| --- | --- | --- | --- |
| Claude Code | `cloud-api-claude-headless-raw-7eedcb912a07` | `cloud-api-claude-headless-manager-80deb1094a09` | `cloud-api-claude-tui-manager-a5b05d9a17c9` |
| Codex | `cloud-api-codex-headless-raw-2b5516f1e015` | `cloud-api-codex-headless-manager-cd48be13034a` | `cloud-api-codex-tui-manager-62133ee44361` |
| Kimi Code | `cloud-api-kimi-headless-raw-c96eb967bb9a` | `cloud-api-kimi-headless-manager-a9911fc582b4` | `cloud-api-kimi-tui-manager-d85e2027f104` |

Each managed locator retains `run.json`, `report.json`, the authoritative managed ID, finalized usage, and private native evidence. Raw locators retain both JSONL captures and the exact provider session ID. TUI locators also retain a private pane capture. All six managed runs report scoped cleanup success; checks confirmed that their tmux sessions were absent and gateway ports were closed. Raw processes had exited and their run state was stopped.

The initial credential was rejected with HTTP 401. The operator updated the ignored env file before the successful fresh runs above. An earlier managed Codex attempt failed because the disposable workdir lacked a Git repository. Preparation now initializes its own Git project, and failed public usage makes prompt execution fail explicitly. Earlier failed runs remain separate private evidence and are excluded from the successful table.

The headless tmux bridge now consumes a mode-0600 environment file and removes it after reading. Its regression test checks both the real child environment and the absence of the secret in tmux/process arguments. This prevents qualification itself from exposing resolved credentials through `--env-json`.

## Self-Hosted Live Prerequisites

No self-hosted model or endpoint references were configured in the selected env file or process environment. The following live lanes were not run:

| Client | Modes | Missing Prerequisites |
| --- | --- | --- |
| Claude Code | Headless and TUI | `HOUMAO_TEST_SELF_HOSTED_MODEL`, `HOUMAO_TEST_SELF_HOSTED_ANTHROPIC_BASE_URL` |
| Codex | Headless and TUI | `HOUMAO_TEST_SELF_HOSTED_MODEL`, `HOUMAO_TEST_SELF_HOSTED_OPENAI_BASE_URL` with Responses support |
| Kimi Code | Headless and TUI | `HOUMAO_TEST_SELF_HOSTED_MODEL`, `HOUMAO_TEST_SELF_HOSTED_OPENAI_BASE_URL` with Chat Completions support, `HOUMAO_TEST_SELF_HOSTED_CONTEXT_WINDOW` |

Hermetic tests exercise both generic cases across every client/mode/surface preparation combination, including a Chat-only descriptor that cannot satisfy Codex. This is configuration evidence, not a claim that an unavailable self-hosted endpoint passed a live test.

## Native Login

Optional live native-login runs were not executed for Claude, Codex, or Kimi because no imported bundle was explicitly selected. Synthetic tests cover supported discovery/import shapes, malformed state, canonical deduplication, bounded searches, source/store byte preservation, private copies, and independent native preparation for all three clients. Controlled manual smoke tests verify explicit selection and scoped cleanup without reading personal login state.

## Automated Evidence

The targeted integration suites exercise actual harmless children and isolated tmux servers for all three clients, both API cases, raw/manager surfaces, and headless/TUI modes. A separate controlled HTTP authority verifies maintained passive headless creation and turns. Real external demo projects verify selected setup/model and Kimi context/capability projection while asserting that subprocess arguments and command logs contain no selected key.

| Check | Result |
| --- | --- |
| `pixi run format` | Passed |
| `pixi run lint` | Passed |
| `pixi run typecheck` | Passed, 420 source files |
| `pixi run test` | 3267 passed, 14 skipped |
| Targeted fixture/consumer/usage integrations | 44 passed |
| `openspec validate refresh-test-agent-fixtures --strict` | Valid |
| Live-key scan of tracked and proposed working-tree files | No selected live secret found |

The targeted integration command was `pixi run python -m pytest tests/integration/agents/test_agent_fixture_launches.py tests/integration/agents/test_agent_fixture_consumers.py tests/integration/agents/realm_controller/test_agent_usage_workflows.py -q --tb=short`. Starlette's existing HTTP-client deprecation warning does not affect the test results.
