# Debug Intent: Houmao 3.0 Interactive Feature Review

Date: 2026-11-18. Updated: 2026-11-18. Status: iteration 1 planned ([plan 1](iterations/2026-11-18-plan-1-dsh-basic-functionality.md), awaiting endpoint/model confirmation and execution). Campaign directory: `context/campaigns/debug/2026-11-18-houmao-3-0-interactive-review/`.

## Problem Statement

Houmao `3.0.0rc1` (tagged at `f99ce02c`, with `devel` at `6207d279`) introduces seven major capabilities over `v2.4.0`: authenticated gateway access (`#84`), execution-owner-aware launch and control (`#81`), DeepSeek Harness `dsh_acp` and `dsh_web` backends (`#74`), native agent home inspection and common-plugin refresh (`#82`), the gateway plugin SDK (`#76`) with `houmao-cccc` chat and deferred Mail (`#77`, `#78`), explicit dual mailbox bindings with bounded Stalwart synchronization (`#79`, `#80`), and durable agent usage records (`#83`). Existing qualification evidence comes mainly from automated unit suites, mocked or stand-in providers, and non-interactive script runs.

Automated passes establish internal protocol compliance, yet they do not show what an operator experiences when driving these features step by step in real time. The campaign evaluates each `3.0.0rc1` capability under live human observation so the reviewer can watch agent execution directly in isolated tmux sessions, browser views, service dashboards, and CLI or HTTP responses, then judge whether each feature works cleanly or requires code, CLI, UX, or documentation revision before `3.0.0` final.

## Starting Evidence

Inspection of the workspace at `6207d279` establishes the following baseline facts:

- **Package and CLI baseline**: [pyproject.toml](../../../../pyproject.toml) declares `Houmao` version `3.0.0rc1`, [packages/houmao-cccc/pyproject.toml](../../../../packages/houmao-cccc/pyproject.toml) declares `houmao-cccc` `0.2.0`, and `dist/` holds `houmao-3.0.0rc1-py3-none-any.whl` and `houmao-3.0.0rc1.tar.gz`. Running `pixi run houmao-mgr --version` prints `houmao-mgr, version 3.0.0rc1`.
- **Installed CLI agents**: Host `PATH` provides `claude` `2.1.325`, `codex-cli` `0.169.0`, `kimi` `2.6.0`, and Bun global `dsh` `0.2.2-rc.1` (npm `latest`), alongside an isolated `dsh` `0.2.2-rc.3` installation at `tmp/dsh/npm-runtime/node_modules/.bin/dsh`. Updated 2026-11-18 per operator direction: DSH version enforcement was revised from exact `==0.2.2rc3` to lower-bounded `>=0.2.2rc1` with no upper cap (accepting release and `rc` builds while rejecting `alpha`/`beta`/`dev`), so both `0.2.2-rc.1` on `PATH` and `0.2.2-rc.3` are usable.
- **Local service installations**: Native CCCC builds and data roots exist under `~/.local/share/houmao-cccc/` and `~/.local/share/houmao-cccc-receiver/`, while Stalwart `v0.15.5` exists under `dockers/email-system/.data/stalwart/` via `udocker`. At campaign creation, ports `8848`, `8849`, `10080`, `10143`, `10587`, and `55432` are not listening.
- **Credential and fixture configuration**: `.env` defines variable names `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL_ANTHROPIC`, and `DEEPSEEK_BASE_URL_OPENAI`. The maintained launch descriptors [cloud-api.yaml](../../../../tests/fixtures/agent-launch/cloud-api.yaml) and [self-hosted.yaml](../../../../tests/fixtures/agent-launch/self-hosted.yaml) define separate `cloud-api` (`deepseek/anthropic_messages` for DSH) and `self-hosted` (`pi-ai/openai_chat` for DSH) lanes. Historical usage fixtures in `tests/fixtures/agent-usage-records/` and archived launch scripts under `openspec/changes/archive/2026-11-13-expose-agent-usage-records/tests/` targeted H20 SGLang `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888` (context window `262144`); at inspection time (`ss -tln`), no local model server or tunnel is listening on `14888`. Prior DSH acceptance records ([dsh-headless-acceptance.md](../../../../docs/reference/run-phase/dsh-headless-acceptance.md)) qualified `cloud-api` (`deepseek-flash`) only and did not live-qualify self-hosted Qwen 3.8.
- **Active host tmux state**: Live user tmux sessions (`mao-1` through `mao-4` and `rsi-1` through `rsi-4`) are running on the default tmux server, so every campaign run must clear `TMUX` and `TMUX_PANE` and target an explicit isolated `-L` or `-S` server.
- **Preliminary documentation discrepancies**: [ROADMAP.md](../../../../ROADMAP.md) still lists `#84` as `Pending` in its summary table even though [CHANGELOG.md](../../../../CHANGELOG.md) and the archived change `2026-11-18-add-authenticated-gateway-access` show `#84` shipped in `3.0.0rc1`. Line 82 of [stalwart-setup-and-first-session.md](../../../../docs/reference/mailbox/operations/stalwart-setup-and-first-session.md) also still states that gateway mail routes remain loopback-only, whereas `#84` replaced that guard with signed `Houmao-SSHSIG` admission.

## Selected Model Lanes

Per operator selection on 2026-11-18, live model-driving tests in this campaign use two explicit provider lanes and never fall back between them or to ambient vendor login state:

| Model Lane | Fixture Case | Configured Source and Route | Notes and Prerequisites |
| --- | --- | --- | --- |
| Self-hosted Qwen 3.8 (primary) | `self-hosted` ([self-hosted.yaml](../../../../tests/fixtures/agent-launch/self-hosted.yaml)) | Explicit local or tunneled OpenAI/Anthropic-compatible endpoint (historically `http://127.0.0.1:14888`, `Qwen/Qwen3.8-27B-FP8`, context `262144`); DSH routes through `pi-ai` (`openai_chat`) | Confirm active endpoint URL, exact model ID, `max_output_tokens`, and DSH reasoning map before live runs; DSH compatibility with Qwen 3.8 is unverified in existing acceptance records |
| DeepSeek API (secondary / reference) | `cloud-api` ([cloud-api.yaml](../../../../tests/fixtures/agent-launch/cloud-api.yaml)) | Project `.env` (`DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL_ANTHROPIC`, `DEEPSEEK_BASE_URL_OPENAI`); DSH routes through `deepseek` (`anthropic_messages`) | Billable API calls; requires explicit model selection and DSH output/reasoning metadata when invoked through [fixture.py](../../../../scripts/agents/test-fixtures/fixture.py) |

## Comparison Arms

This campaign evaluates each `3.0.0rc1` feature area across two perspectives: the documented contract (`docs/reference/`, `CHANGELOG.md`, `openspec/specs/`) versus live human-watched interactive execution.

| Arm | Feature Area | What the Human Watches Interactively | Key Surfaces and Services |
| --- | --- | --- | --- |
| F1 | Authenticated gateway access (`#84`) | Empty admin roster risk, SSHSIG key enrollment and rotation, self-vs-admin-vs-public access failures, public prompt budget, and reverse-proxy advertised endpoint behavior | `houmao-mgr agents single|self gateway`, `GatewayClient`, `POST /v1/auth/challenge`, `GET /v1/endpoint`, `houmao-passive-server` |
| F2 | Execution-owner-aware launch and control (`#81`) | Cross-user `sudo` or `ssh` launch into target-owned homes, isolated tmux socket viewing, owner-boundary denials, and `reconcile`/`forget` locator recovery | `~/.config/houmao/executors/*.yaml`, `houmao-mgr internals executor serve-stdio`, `admin executors`, `sudo`, local `sshd` |
| F3 | DSH `dsh_acp` and `dsh_web` backends (`#74`) | ACP headless turns, exact resume, and cancellation in tmux versus `dsh_web` live browser UI alongside API Peer (`interactions=none`), admission refusal (`ready_only`), and human/API coexistence | `dsh` `0.2.2-rc.3`, `dsh-setup.yaml`, `houmao-mgr project specialist|profile|agents`, Chromium browser view |
| F4 | Native home inspection and common-plugin refresh (`#82`) | Editing skills or MCP definitions externally, running `home`, `refresh --check`, and `refresh`, and observing live discovery without restarting or regenerating launch config | `houmao-mgr agents single|self home|refresh`, `/v1/native-home`, `/v1/control/refresh`, DSH vs Claude/Codex/Kimi |
| F5 | Gateway plugins (`#76`) and `houmao-cccc` (`#77`, `#78`) | Attaching `houmao-cccc` without restarting the body, watching live CCCC Web UI and agent panes exchange `request_reply` chat and deferred Mail (`status`, `cursor`, `peek`, `read`, receipts) | `houmao.gateway.plugins`, `packages/houmao-cccc`, `houmao-cccc` CLI, local CCCC receiver on `8849` |
| F6 | Dual mailbox bindings and bounded Stalwart sync (`#79`, `#80`) | Live `mailbox online attach|refresh|reconnect|detach` on a running agent, coexistence of `offline` and `online` slots, bounded metadata-only `list`, and periodic notifier wakeups inside the watched pane | Stalwart `v0.15.5` on `10080`, `houmao-mgr agents single|self mail|mailbox`, `/v1/mail/*` |
| F7 | Durable agent usage records (`#83`) | Inspecting `GET /v1/usage` and passive-server `/usage` pages after real watched turns, interrupts, resumes, and restarts, comparing against raw provider journals | `GET /v1/usage`, `GET /houmao/agents/{agent_ref}/usage`, `session.v4.jsonl`, `<session-root>/usage/records.sqlite3` |

## Scope and Implementation Boundary

- **In scope**: Human-watched interactive walkthroughs executed in isolated scratch workspaces and external runtime/auth roots, using explicit `-L` or `-S` tmux servers so the human can attach (`tmux -L <name> attach`) and observe every turn live, alongside browser UIs, CCCC Web UI, Stalwart logs, gateway HTTP traffic, and CLI outputs. Every step pauses at human review checkpoints before advancing.
- **Read-only assets**: Production source code under `src/houmao/` and `packages/houmao-cccc/`, committed tests under `tests/`, OpenSpec specifications under `openspec/`, active user tmux sessions (`mao-1..4`, `rsi-1..4`) on the default server, and secret credential files remain untouched.
- **Out of scope**: Postponed Pi backend (`#75`), live Docker container execution (no Docker daemon or socket is present in this environment per [execution README](../../../../tests/integration/execution/README.md)), physical multi-host networking across separate machines, and direct product code edits during diagnostic runs.

## Success Criteria

- Interactive execution protocols and live watch procedures (tmux attach targets, browser URLs, log tails, and pause checkpoints) are defined and run for the prioritized `3.0.0rc1` feature arms.
- Each tested feature arm receives an evidence-backed review disposition: **Works as designed**, **Works with caveats or UX friction**, or **Needs revision**.
- Observed issues, confusing CLI or browser ergonomics, unclear error messages, observability gaps, and documentation mismatches are captured with exact commands and outputs in `evidences/`, analyzed in `discussions/`, and synthesized into prioritized revision candidates in `reports/`.

## No-Product-Change Declaration

This campaign is an isolated interactive diagnostic and review effort. It does not authorize modifying production code under `src/houmao/` or `packages/houmao-cccc/`, modifying existing tests under `tests/`, or editing OpenSpec specifications. Any fixes or revisions identified by human review require separate explicit approval outside this campaign.

## Key Questions and Iterations

Active links:

- [KQ-1: DSH Basic Functionality With Houmao](key-questions/KQ-1-dsh-basic-functionality.md)
- [Iteration 1: DSH Basic Functionality With Houmao](iterations/2026-11-18-plan-1-dsh-basic-functionality.md)

Planned candidate questions for later iterations:

- **KQ-2 (Gateway Auth, Passive Server, and Remote Endpoint UX)**: Is the SSHSIG enrollment, self-versus-admin boundary, endpoint advertisement, and usage inspection flow intuitive and defect-free in interactive use?
- **KQ-3 (Native Home Inspection and Common-Plugin Refresh UX)**: Do `home`, `refresh --check`, and `refresh` behave clearly under live external skill and MCP edits across DSH and secondary CLIs?
- **KQ-4 (Dual Mailbox, Stalwart, and `houmao-cccc` Live Coordination)**: Do live online mailbox attach/detach, bounded mail operations, notifier wakeups, and `houmao-cccc` chat/deferred Mail work cleanly side by side while watched live?
- **KQ-5 (Execution-Owner Switching UX)**: Does `sudo` or `ssh` owner-aware launch, control, and `reconcile`/`forget` recovery behave transparently when observed across operator and owner boundaries?
